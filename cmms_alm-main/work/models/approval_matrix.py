"""
Approval Matrix for the five-stage Work Request flow.

Two kinds of step:
  * Named — a sign-off. One accountable person, chosen here by the Super Admin:
    the APPROVER (Category Manager) and CLIENT rep per facility, and the
    HEAD OF FINANCE & TREASURY company-wide.
  * Team — preparing or checking work. Everyone holding the role (in scope) can act;
    nobody is chosen. Site Managers per facility; Procurement & Store, Central
    Operations, AP Officers and Internal Control company-wide; the CONTRACTOR is
    the staff of the Work Order's vendor.

A facility is switched on (`is_live`) only when every named step has an active,
valid person and every team has at least one active member. Nothing reads
`is_live` yet; the stage screens will.
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

SLOT_LABELS = {
    'requester': 'REQUESTER (Site Manager)',
    'approver': 'APPROVER (Category Manager)',
    'client_rep': 'CLIENT (Client Contract Rep)',
    'procurement': 'PROCUREMENT AND STORE',
    'central_operation': 'CENTRAL OPERATION',
    'contractor': 'CONTRACTOR (Vendor)',
    'ap_officer': 'AP OFFICER',
    'reviewer': 'REVIEWER (Internal Control)',
    'head_of_finance': 'HEAD OF FINANCE & TREASURY',
}

# Named steps → the role their person must hold.
FACILITY_SLOTS = {
    'approver': 'APPROVER',
    'client_rep': 'CLIENT',
}
COMPANY_SLOTS = {
    'head_of_finance': 'HEAD OF FINANCE & TREASURY',
}

# Team steps → (role, scope). 'facility': members must be assigned to the facility.
TEAM_SLOTS = {
    'requester': ('REQUESTER', 'facility'),
    'procurement': ('PROCUREMENT AND STORE', 'company'),
    'central_operation': ('CENTRAL OPERATION', 'company'),
    'ap_officer': ('AP OFFICER', 'company'),
    'reviewer': ('REVIEWER', 'company'),
}
# The CONTRACTOR is a team too, but its members come from each Work Order's vendor.
CONTRACTOR = 'contractor'

# Stage → (raises, reviews, approves), following the Workflow Table.
STAGES = [
    ('Work Request', 'requester', 'approver', 'client_rep'),
    ('Work Order', 'procurement', 'approver', 'client_rep'),
    ('Completion (WCC)', 'requester', 'central_operation', 'approver'),
    ('Vendor Invoice', CONTRACTOR, 'ap_officer', 'head_of_finance'),
    ('Payment', 'ap_officer', 'reviewer', 'head_of_finance'),
]


def _person():
    return models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )


def _who(user):
    return user.name.strip() or user.email


def assigned_to(user, facility):
    from cmms_instanta.permissions import accessible_facilities

    return accessible_facilities(user).filter(pk=facility.pk).exists()


def slot_error(slot, user, facility=None):
    """Why `user` cannot be the named person for `slot` (at `facility`), or None if they can."""
    label = SLOT_LABELS[slot]
    if slot == 'client_rep' and facility is not None and facility.client_id is None:
        return "This facility has no client. Link it to a client before choosing the Client Contract Rep."
    if user is None:
        return f"{label} is not set."
    role = FACILITY_SLOTS.get(slot) or COMPANY_SLOTS[slot]
    if not user.is_active:
        return f"{_who(user)} ({label}) is inactive."
    if user.roles != role:
        return f"{_who(user)} does not hold the {role} role needed for {label}."
    if facility is None:
        return None
    if slot == 'client_rep':
        if not (user.access_to_all_clients or user.clients.filter(pk=facility.client_id).exists()):
            return f"{_who(user)} does not belong to this facility's client ({facility.client.name})."
    elif not assigned_to(user, facility):
        return f"{_who(user)} is not assigned to {facility.name}."
    return None


def team_members(slot, facility=None):
    """Active users who belong to the team `slot` (at `facility`, for facility teams)."""
    role, scope = TEAM_SLOTS[slot]
    users = get_user_model().objects.filter(roles=role, is_active=True)
    if scope == 'facility':
        users = users.filter(Q(access_to_all_facilities=True) | Q(facility=facility)).distinct()
    return users


def team_problems(facility):
    problems = []
    for slot, (role, scope) in TEAM_SLOTS.items():
        if not team_members(slot, facility).exists():
            where = f" assigned to {facility.name}" if scope == 'facility' else ''
            problems.append(f"No active user holds the {role} role{where}.")
    return problems


class CompanyApprovers(models.Model):
    """The company-wide named step of the Approval Matrix. One row, edited by the Super Admin."""

    head_of_finance = _person()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Company-wide approvers"
        verbose_name_plural = "Company-wide approvers"

    def __str__(self):
        return "Company-wide approvers"

    @classmethod
    def current(cls):
        approvers, _ = cls.objects.get_or_create(pk=1)
        return approvers

    def problems(self):
        return [error for slot in COMPANY_SLOTS if (error := slot_error(slot, getattr(self, slot)))]


class ApprovalMatrix(models.Model):
    """The facility's named steps, and whether the facility uses the five-stage flow."""

    facility = models.OneToOneField('facility.Facility', on_delete=models.CASCADE, related_name='approval_matrix')
    approver = _person()
    client_rep = _person()
    is_live = models.BooleanField(default=False, help_text="The facility uses the five-stage flow.")
    went_live_at = models.DateTimeField(null=True, blank=True)
    went_live_by = _person()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Approval matrix"
        verbose_name_plural = "Approval matrix"

    def __str__(self):
        return f"Approval matrix · {self.facility}"

    def named_person(self, slot):
        if slot in COMPANY_SLOTS:
            return getattr(CompanyApprovers.current(), slot)
        return getattr(self, slot)

    def problems(self):
        """Everything stopping this facility from going live; empty when it is ready."""
        named = [error for slot in FACILITY_SLOTS
                 if (error := slot_error(slot, getattr(self, slot), self.facility))]
        return named + CompanyApprovers.current().problems() + team_problems(self.facility)

    def chain(self):
        """Who raises, reviews and approves at each stage, and whether each step is named or a team."""
        kind = lambda slot: 'named' if slot in FACILITY_SLOTS or slot in COMPANY_SLOTS else 'team'
        return [
            {'stage': stage, 'raises': raises, 'reviews': reviews, 'approves': approves,
             'kinds': {'raises': kind(raises), 'reviews': kind(reviews), 'approves': kind(approves)}}
            for stage, raises, reviews, approves in STAGES
        ]

    def go_live(self, user):
        problems = self.problems()
        if problems:
            raise ValidationError(problems)
        self.is_live = True
        self.went_live_at = timezone.now()
        self.went_live_by = user
        self.save(update_fields=['is_live', 'went_live_at', 'went_live_by', 'updated_at'])

    def switch_off(self):
        self.is_live = False
        self.save(update_fields=['is_live', 'updated_at'])


def eligible(user, slot, facility, vendor=None):
    """
    May `user` act on step `slot` of a job at `facility`? The one check every stage uses.

    Named step: only the named person. Team step: anyone holding the role, in scope.
    CONTRACTOR: staff of the job's `vendor`. (Stand-ins arrive with delegation.)
    """
    if user is None or not user.is_active:
        return False
    if slot == CONTRACTOR:
        return user.roles == 'CONTRACTOR' and vendor is not None and user.vendor_id == vendor.pk
    if slot in TEAM_SLOTS:
        role, scope = TEAM_SLOTS[slot]
        return user.roles == role and (scope == 'company' or assigned_to(user, facility))
    if slot in COMPANY_SLOTS:
        return getattr(CompanyApprovers.current(), f'{slot}_id') == user.pk
    matrix = ApprovalMatrix.objects.filter(facility=facility).first()
    return matrix is not None and getattr(matrix, f'{slot}_id') == user.pk
