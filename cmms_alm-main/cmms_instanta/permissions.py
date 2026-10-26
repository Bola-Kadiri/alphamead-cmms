from rest_framework.permissions import SAFE_METHODS, BasePermission

# Company-wide roles of the five-stage Work Request flow.
COMPANY_WIDE_ROLES = {'CENTRAL OPERATION', 'AP OFFICER', 'HEAD OF FINANCE & TREASURY'}

# Roles that can see every site regardless of their own facility assignments.
UNRESTRICTED_FACILITY_ROLES = {'SUPER ADMIN', 'ADMIN'} | COMPANY_WIDE_ROLES

# Roles that approve and disburse payment requisitions (formerly FINANCE).
FINANCE_ROLES = {'HEAD OF FINANCE & TREASURY'}

# Roles that see every work request, work order and completion, and the
# company-wide dashboard. Seeing is not acting: actions keep their own checks.
SEE_ALL_ROLES = {'SUPER ADMIN', 'ADMIN', 'AP OFFICER', 'CENTRAL OPERATION'} | FINANCE_ROLES

# Roles that see every invoice (CENTRAL OPERATION does not).
SEE_ALL_INVOICE_ROLES = {'SUPER ADMIN', 'ADMIN', 'AP OFFICER'} | FINANCE_ROLES


def accessible_facilities(user):
    """
    The Facility queryset `user` is allowed to see. Privileged roles (and
    anyone flagged access_to_all_facilities, or a Django superuser) see
    every site; everyone else is scoped to `user.facility` — the
    assignment already used by work/views.py's own facility dropdown.
    """
    from facility.models import Facility

    if not getattr(user, 'is_authenticated', False):
        return Facility.objects.none()

    # A CLIENT sees only the facilities linked to their client organisation(s);
    # the facility-level "all facilities" flag never applies to them.
    if getattr(user, 'roles', None) == 'CLIENT':
        if getattr(user, 'access_to_all_clients', False):
            return Facility.objects.filter(client__isnull=False)
        return Facility.objects.filter(client__in=user.clients.all())

    if (
        user.is_superuser
        or getattr(user, 'access_to_all_facilities', False)
        or getattr(user, 'roles', None) in UNRESTRICTED_FACILITY_ROLES
    ):
        return Facility.objects.all()
    return user.facility.all()


class SuperAdminWriteOrReadOnly(BasePermission):
    """
    Reference data that drives payments (categories/subcategories — including
    the known-cost tick — and vendors with their bank details): every logged-in
    user can view it (the work order forms need it), but only a Super Admin can
    add, edit or delete it.
    """
    message = "Only a Super Admin can add, edit or delete this."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return user.is_superuser or getattr(user, 'roles', None) == 'SUPER ADMIN'


class RoleBasedPermission(BasePermission):
    """Single permission class that checks access based on role and feature"""
    ROLE_FEATURES = {
        'SUPER ADMIN': {
            'work_request': ['view', 'edit'],
            'work_order': ['view', 'edit'],
            'pending_ppm': ['view', 'edit'],
            'requisition': ['view', 'edit'],
            'ppm_setting': ['view', 'edit'],
            'asset_register': ['view', 'edit'],
            'inventory_register': ['view', 'edit'],
            'item_request': ['view', 'edit'],
            'inventory_adjustment': ['view', 'edit'],
            'transfer_form': ['view', 'edit'],
            'movement_history': ['view', 'edit'],
            'report': ['view', 'edit'],
            'reference': ['view', 'edit'],
            'django_admin': ['view', 'edit'],
            'comment': ['view', 'edit'],
        },
        'ADMIN': {
            'work_request': ['view', 'edit'],
            'work_order': ['view', 'edit'],
            'pending_ppm': ['view', 'edit'],
            'requisition': ['view', 'edit'],
            'ppm_setting': ['view', 'edit'],
            'asset_register': ['view', 'edit'],
            'inventory_register': ['view', 'edit'],
            'item_request': ['view', 'edit'],
            'inventory_adjustment': ['view', 'edit'],
            'transfer_form': ['view', 'edit'],
            'movement_history': ['view', 'edit'],
            'report': ['view', 'edit'],
            'reference': ['view', 'edit'],
            'comment': ['view', 'edit'],
        },
        'PROCUREMENT AND STORE': {
            'work_request': ['view', 'edit'],
            'work_order': ['view', 'edit'],
            'pending_ppm': ['view', 'edit'],
            'requisition': ['view', 'edit'],
            'ppm_setting': ['view', 'edit'],
            'asset_register': ['view'],
            'comment': ['view', 'edit'],
        },
        'APPROVER': {
            'work_request': ['view'],
            'work_order': ['view', 'edit'],
            'pending_ppm': ['view', 'edit'],
            'requisition': ['view', 'edit'],
            'ppm_setting': ['view', 'edit'],
            'asset_register': ['view'],
            'comment': ['view', 'edit'],
        },
        'REQUESTER': {
            'work_request': ['view', 'edit'],
            'work_order': ['view', 'edit'],
            'pending_ppm': ['view', 'edit'],
            'requisition': ['view', 'edit'],
            'ppm_setting': ['view', 'edit'],
            'asset_register': ['view'],
            'comment': ['view', 'edit'],
        },
        # View-only; which endpoints a CLIENT may reach at all is decided by
        # ClientAccessMiddleware (default deny), and what they see is scoped to
        # their client's facilities in each viewset.
        'CLIENT': {
            'work_request': ['view'],
            'work_order': ['view'],
            'requisition': ['view'],   # facility list (FacilityViewSet uses this feature)
        },
        'REVIEWER': {
            'work_request': ['view'],
            'work_order': ['view'],
            'pending_ppm': ['view'],
            'requisition': ['view'],
            'ppm_setting': ['view'],
            'asset_register': ['view'],
            'inventory_register': ['view'],
            'item_request': ['view'],
            'report': ['view'],
            'reference': ['view'],
            'comment': ['view'],
        },
        'Facility Account': {
            'work_request': ['view'],
            'work_order': ['view'],
            'pending_ppm': ['view'],
            'requisition': ['view'],
            'ppm_setting': ['view'],
            'asset_register': ['view'],
            'inventory_register': ['view'],
            'item_request': ['view'],
            'report': ['view'],
            'reference': ['view'],
            'comment': ['view'],
        },
        'Facility Store': {
            'work_request': ['view', 'edit'],
            'work_order': ['view', 'edit'],
            'pending_ppm': ['view', 'edit'],
            'requisition': ['view', 'edit'],
            'ppm_setting': ['view', 'edit'],
            'asset_register': ['view', 'edit'],
            'inventory_register': ['view', 'edit'],
            'item_request': ['view', 'edit'],
            'inventory_adjustment': ['view', 'edit'],
            'transfer_form': ['view', 'edit'],
            'movement_history': ['view', 'edit'],
            'report': ['view', 'edit'],
            'reference': ['view', 'edit'],
            'comment': ['view', 'edit'],
        },
        'Facility View': {
            'work_request': ['view'],
            'work_order': ['view'],
            'pending_ppm': ['view'],
            'requisition': ['view'],
            'ppm_setting': ['view'],
            'asset_register': ['view'],
            'inventory_register': ['view'],
            'item_request': ['view'],
            'inventory_adjustment': ['view'],
            'transfer_form': ['view'],
            'movement_history': ['view'],
            'report': ['view'],
            'reference': ['view'],
            'comment': ['view'],
        },
        # The payment actions are gated inside the views.
        'HEAD OF FINANCE & TREASURY': {
            'work_request': ['view'],
            'work_order': ['view'],
            'requisition': ['view'],
            'pending_ppm': ['view'],
            'report': ['view'],
            'comment': ['view'],
        },
        'AP OFFICER': {
            'work_request': ['view'],
            'work_order': ['view'],
            'requisition': ['view'],
            'pending_ppm': ['view'],
            'report': ['view'],
            'comment': ['view'],
        },
        'CENTRAL OPERATION': {
            'work_request': ['view'],
            'work_order': ['view'],
            'requisition': ['view'],   # facility list (FacilityViewSet uses this feature)
            'pending_ppm': ['view'],
            'report': ['view'],
            'comment': ['view'],
        },
        # No screens yet: the vendor portal (jobs, invoices) arrives with Stage 4.
        'CONTRACTOR': {},
    }

    def has_permission(self, request, view):
        """Check if the user has permission for the specified feature"""
        if not request.user.is_authenticated:
            return False
        
        # Get the feature from the view
        feature = getattr(view, 'feature', None)
        if not feature:
            return False

        # Get the user's role
        user_role = request.user.roles
        if user_role not in self.ROLE_FEATURES:
            return False

        # Workflow actions use POST but are gated by role checks inside the view,
        # not the generic 'edit' permission — only 'view' access is needed here.
        approve_actions = {
            # legacy names
            'approve_request', 'reject_request', 'approve_order', 'approve', 'review', 'reject',
            # work-request workflow actions
            'cp_approve', 'cp_reject',
            'reviewer_approve', 'reviewer_reject',
            'final_approve', 'final_reject',
            'resubmit',
            # five-stage flow actions — gated by the action rules inside
            'flow_review', 'flow_send_back', 'flow_resubmit', 'flow_approve', 'flow_reject',
            'flow_start', 'flow_pricing', 'flow_submit', 'flow_accept',
            'flow_details', 'flow_evidence', 'flow_verify', 'flow_return',
            # payment-requisition workflow — HEAD OF FINANCE & TREASURY only has 'view' on the
            # requisition feature; the real gate is the role check inside
            # PaymentRequisitionViewSet.disburse itself.
            'disburse',
            # Raise Payment large bills — gated inside WorkOrderViewSet.
            'procurement_submit', 'procurement_return', 'raise_payment_resubmit',
            # ppm / other
            'approve_order',
        }
        view_action = getattr(view, 'action', None)
        if view_action in approve_actions:
            required_action = 'view'
        else:
            required_action = 'edit' if request.method in ['POST', 'PUT', 'PATCH', 'DELETE'] else 'view'

        return required_action in self.ROLE_FEATURES[user_role].get(feature, [])
    

class RoleBasedPermissionMixin:
    """Mixin for DRF ViewSets to apply role-based permissions"""
    permission_classes = [RoleBasedPermission]

    def get_permissions(self):
        return [permission() for permission in self.permission_classes]
