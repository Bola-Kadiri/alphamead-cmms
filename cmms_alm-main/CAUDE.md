# Work Request Management System — Django Implementation Guide

## Project Overview
A Django + React JS CMMS application implementing a multi-stage work request lifecycle
with Procurement & Store commercial validation, Reviewer QA, and Approver executive authorization.
Six roles are already defined in the system — do NOT create new roles or rename existing ones.

---

## Bash Commands
- `python manage.py runserver` — Start dev server
- `python manage.py makemigrations` — Generate migrations after model changes
- `python manage.py migrate` — Apply migrations
- `python manage.py test work_requests` — Run the full test suite
- `python manage.py createsuperuser` — Bootstrap admin user
- `python manage.py shell_plus` — Django shell with auto-imports (requires django-extensions)
- `pip install -r requirements.txt` — Install dependencies
- `flake8 . --max-line-length=100` — Lint check
- `black . --line-length 100` — Auto-format

---

## Existing Roles — Do NOT Rename or Add New Ones

These six Django Groups are already in the system. Reference them by exact string via `constants.py` only.

```python
# constants.py — single source of truth for role names
class Role:
    SUPER_ADMIN        = "Super Admin"
    ADMIN              = "Admin"
    PROCUREMENT_STORE  = "Procurement & Store"
    REVIEWER           = "Reviewer"
    APPROVER           = "Approver"
    REQUESTER          = "Requester"
```

> Procurement & Store is a single Django Group. Use `Role.PROCUREMENT_STORE` everywhere.
> Permission check: `user.groups.filter(name=Role.PROCUREMENT_STORE).exists()`

---

## Role and Permission Matrix

| Role        | Work Request Permissions                                                                     | Admin Access       |
|-------------|----------------------------------------------------------------------------------------------|--------------------|
| Super Admin | Full CRUD on all records; manage users, groups, and system config                           | Django Admin + all |
| Admin       | Full CRUD on all records; manage users and groups (no system config)                        | Django Admin       |
| Procurement & Store | Step 2 Path A: approve + generate PO; Path B: change vendor + new PO + reject  | No                 |
| Reviewer    | Step 3: three-way audit; approve (Reviewed) or reject with mandatory reason                 | No                 |
| Approver    | Step 4: final approve with digital signature; reject with mandatory reason                  | No                 |
| Requester   | Create request; attach invoice; select route in fixed order: Procurement & Store → Reviewer → Approver; resubmit after rejection  | No                 |

Super Admin and Admin can view ALL requests regardless of assignment mapping.
All other roles see only requests where they are the assigned cp_handler, reviewer, or approver,
or where they are the requester.

Never check user.groups inline in views — always delegate to permissions.py.

---

## Architecture and Project Layout

```
work_request_system/
├── CLAUDE.md
├── manage.py
├── requirements.txt
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   └── wsgi.py
└── work_requests/
    ├── models.py          # Core domain models
    ├── managers.py        # Custom QuerySet / Manager logic
    ├── views.py           # Class-based views per role action
    ├── serializers.py     # DRF serializers
    ├── services.py        # ALL business logic and state machine transitions
    ├── permissions.py     # Role-based permission classes
    ├── signals.py         # Post-transition hooks
    ├── forms.py           # Django forms
    ├── admin.py           # Admin with inline AuditLog
    ├── urls.py
    ├── tasks.py           # Celery async tasks
    ├── constants.py       # Role strings, status codes — single source of truth
    └── tests/
        ├── factories.py          # factory_boy fixtures for all 6 roles
        ├── test_models.py
        ├── test_services.py      # All 6 roles x all transition paths
        ├── test_views.py
        └── test_permissions.py
```

---

## Domain Model Specification

### WorkRequest
```python
class WorkRequest(models.Model):
    # Identity
    request_id    = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    # Routing — Requester selects in strict order at creation: cp_handler → reviewer → approver
    # All three must be selected before the request can be submitted. Read-only after submission.
    requester     = models.ForeignKey(User, related_name="created_requests", on_delete=models.PROTECT)
    cp_handler    = models.ForeignKey(User, related_name="cp_queue", on_delete=models.PROTECT)
    # Step 1 — must belong to Procurement & Store group (validated in serializer)
    reviewer      = models.ForeignKey(User, related_name="review_queue", on_delete=models.PROTECT)
    # Step 2 — must belong to Reviewer group (validated in serializer)
    approver      = models.ForeignKey(User, related_name="approval_queue", on_delete=models.PROTECT)
    # Step 3 — must belong to Approver group (validated in serializer)

    # Invoice and PO
    invoice       = models.FileField(upload_to="invoices/%Y/%m/")
    vendor        = models.ForeignKey("Vendor", null=True, blank=True, on_delete=models.PROTECT)
    purchase_order = models.OneToOneField("PurchaseOrder", null=True, blank=True, on_delete=models.SET_NULL)

    # State — transition ONLY via services.py
    status        = models.CharField(max_length=40, choices=Status.choices,
                                     default=Status.PENDING_REVIEW, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "cp_handler"]),
            models.Index(fields=["status", "reviewer"]),
            models.Index(fields=["status", "approver"]),
            models.Index(fields=["status", "requester"]),
        ]
```

### Status Constants
```python
# constants.py
class Status(models.TextChoices):
    PENDING_REVIEW    = "PENDING_REVIEW",   "Pending Review"
    CP_APPROVED       = "CP_APPROVED",      "C&P Approved"
    REJECTED_VENDOR   = "REJECTED_VENDOR",  "Rejected – Vendor Changed"
    REVIEWED          = "REVIEWED",         "Reviewed"
    REVIEWER_REJECTED = "REVIEWER_REJECTED","Reviewer Rejected"
    FULLY_APPROVED    = "FULLY_APPROVED",   "Fully Approved"
    APPROVER_REJECTED = "APPROVER_REJECTED","Approver Rejected"
```

### AuditLog — append-only, never update or delete rows
```python
class AuditLog(models.Model):
    work_request = models.ForeignKey(WorkRequest, related_name="audit_logs", on_delete=models.CASCADE)
    actor        = models.ForeignKey(User, on_delete=models.PROTECT)
    actor_role   = models.CharField(max_length=40)  # snapshot role at time of action
    from_status  = models.CharField(max_length=40)
    to_status    = models.CharField(max_length=40)
    reason       = models.TextField(blank=True)      # mandatory on all rejection paths
    timestamp    = models.DateTimeField(auto_now_add=True)
    meta         = models.JSONField(default=dict)    # {"po_number": ..., "signature": ...}

    class Meta:
        ordering = ["timestamp"]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("AuditLog entries are immutable.")
        super().save(*args, **kwargs)
```

### PurchaseOrder
```python
class PurchaseOrder(models.Model):
    po_number  = models.CharField(max_length=50, unique=True)
    vendor     = models.ForeignKey("Vendor", on_delete=models.PROTECT)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    amount     = models.DecimalField(max_digits=14, decimal_places=2)
```

---

## State Machine — Transition Rules (implement in services.py only)

```
PENDING_REVIEW
    --> CP_APPROVED        actor: Procurement & Store     Path A
    --> REJECTED_VENDOR    actor: Procurement & Store     Path B — reason required, new vendor required

CP_APPROVED
    --> REVIEWED           actor: Reviewer                Path A — three-way audit must pass
    --> REVIEWER_REJECTED  actor: Reviewer                Path B — reason required

REVIEWED
    --> FULLY_APPROVED     actor: Approver                Path A — ledger commit + digital signature
    --> APPROVER_REJECTED  actor: Approver                Path B — reason required

REJECTED_VENDOR | REVIEWER_REJECTED | APPROVER_REJECTED
    --> PENDING_REVIEW     actor: Requester               Requester corrects and resubmits
```

### Service Function Signatures
```python
# services.py — raise TransitionError for wrong role or wrong current status

class TransitionError(Exception):
    """Raised when a transition is illegal."""

def cp_approve(request_id: UUID, actor: User) -> WorkRequest: ...
def cp_reject_vendor(request_id: UUID, actor: User, new_vendor_id: int, reason: str) -> WorkRequest: ...
def reviewer_approve(request_id: UUID, actor: User) -> WorkRequest: ...
def reviewer_reject(request_id: UUID, actor: User, reason: str) -> WorkRequest: ...
def approver_approve(request_id: UUID, actor: User) -> WorkRequest: ...
def approver_reject(request_id: UUID, actor: User, reason: str) -> WorkRequest: ...
def requester_resubmit(request_id: UUID, actor: User) -> WorkRequest: ...
def commit_to_ledger(work_request: WorkRequest, actor: User) -> None: ...
```

Every service function must:
1. Assert actor has the correct role — raise TransitionError if not.
2. Assert current status allows the transition — raise TransitionError if not.
3. Perform all DB writes inside transaction.atomic().
4. Write AuditLog (with actor_role snapshot) in the same atomic block.

---

## Requester UI Constraints

### Route Selection — Strict Order Enforced
The creation form presents assignees in a fixed, sequential order. Each step only unlocks
after the previous one is filled. The UI must reflect this order and the API serializer
must validate it server-side:

```
Step 1 — Select Procurement & Store handler  (cp_handler)
    ↓  (unlocks after Step 1 is selected)
Step 2 — Select Reviewer                     (reviewer)
    ↓  (unlocks after Step 2 is selected)
Step 3 — Select Approver                     (approver)
    ↓  (unlocks after Step 3 is selected)
Submit request
```

### Serializer Validation Rules (enforce server-side, not just UI)
```python
def validate(self, data):
    cp = data.get("cp_handler")
    reviewer = data.get("reviewer")
    approver = data.get("approver")

    if not cp.groups.filter(name=Role.PROCUREMENT_STORE).exists():
        raise ValidationError({"cp_handler": "Must be a Procurement & Store member."})
    if not reviewer.groups.filter(name=Role.REVIEWER).exists():
        raise ValidationError({"reviewer": "Must be a Reviewer."})
    if not approver.groups.filter(name=Role.APPROVER).exists():
        raise ValidationError({"approver": "Must be an Approver."})
    # Prevent a user filling more than one role on the same request
    if len({cp.pk, reviewer.pk, approver.pk}) < 3:
        raise ValidationError("cp_handler, reviewer, and approver must be different users.")
    return data
```

### Post-Submission Rules
- After submission the request is read-only for the Requester.
- Requester can edit/resubmit ONLY when status is: REJECTED_VENDOR, REVIEWER_REJECTED, or APPROVER_REJECTED.
- On resubmit, Requester may update invoice and re-select all three assignees, respecting the same order and validation rules above.

---

## Three-Way Audit Logic (Reviewer Step)

```python
@dataclass
class ThreeWayAuditResult:
    passed: bool
    mismatches: list[str]   # human-readable discrepancy descriptions

def perform_three_way_audit(work_request: WorkRequest) -> ThreeWayAuditResult: ...
```

Compares: (1) original WorkRequest fields, (2) PurchaseOrder from Procurement & Store,
(3) attached invoice metadata. Reviewer UI surfaces mismatches when passed=False.
The approve action is blocked when passed=False unless Reviewer logs an explicit override reason.

---

## Ledger Commit (Approver Step)

commit_to_ledger() must:
1. Create immutable LedgerEntry: request_id, po_number, amount, approver,
   digital_signature (HMAC-SHA256 of canonical fields), committed_at.
2. Set WorkRequest.status = FULLY_APPROVED atomically.
3. Append AuditLog with meta={"ledger_entry_id": ..., "signature": ...}.
4. Fire Django signal request_fully_approved for downstream consumers (ERP, notifications).

---

## API Layer (Django REST Framework)

- Separate @action per transition — no single god endpoint.
- Serializer must reject blank reason on all rejection paths (ValidationError).
- All responses include: request_id, status, updated_at.
- List endpoints: PageNumberPagination, page_size=25.
- Filter queryset by: status, requester, cp_handler, reviewer, approver.

---

## Real-Time Tracking Dashboard

- Polling endpoint: GET /api/requests/{id}/status/
  Returns: status, active owner name, full AuditLog list (with actor_role snapshots).
- Stakeholders who can access: requester, cp_handler, reviewer, approver, Admin, Super Admin.
- Super Admin and Admin bypass assignment checks and can access all requests.

---

## Testing — Required per Service Function

1. Happy path for the correct role.
2. Wrong role actor → TransitionError.
3. Wrong current status → TransitionError.
4. Rejection with blank reason → ValidationError.

Create one factory per role in tests/factories.py:
```python
# One factory per role — 6 total
class ProcurementStoreUserFactory(UserFactory):
    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        self.groups.add(Group.objects.get(name=Role.PROCUREMENT_STORE))

# Also create: RequesterFactory, ReviewerFactory, ApproverFactory,
#              AdminFactory, SuperAdminFactory
```

Coverage target: >= 90% for services.py and models.py.

---

## Key Constraints — Never Violate

- Never set work_request.status outside services.py.
- Never mutate or delete AuditLog rows.
- Never skip a stage (e.g. PENDING_REVIEW directly to REVIEWED).
- Never hardcode role strings outside constants.py.
- Never check user.groups inline in views — always use permissions.py.
- Always wrap status transition + AuditLog write in transaction.atomic().
- Always require non-empty reason on rejection paths — enforce at serializer level, not just UI.
- Always snapshot actor_role into AuditLog at write time.

---

## Workflow Reminders for Claude Code

- New transition: update constants.py (if new status) + services.py + permissions.py + tests.
- Model change: makemigrations → inspect generated file → migrate.
- Before PR: flake8, black --check, full test suite passing.
- Implement and test ONE role at a time. Commit after each role passes all tests.
  Recommended order: Super Admin → Admin → Requester → Procurement & Store → Reviewer → Approver.

---

## Dependencies (requirements.txt baseline)

```
django>=4.2,<5.0
djangorestframework>=3.14
django-filter>=23.0
django-extensions>=3.2
channels>=4.0
celery>=5.3
django-rules>=3.3
factory-boy>=3.3
pytest-django>=4.7
black>=24.0
flake8>=7.0
```
