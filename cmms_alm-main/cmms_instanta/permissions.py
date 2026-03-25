from rest_framework.permissions import BasePermission

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
            'comment': ['view', 'edit'],
        },
        'APPROVER': {
            'work_order': ['view', 'edit'],
            'pending_ppm': ['view', 'edit'],
            'requisition': ['view', 'edit'],
            'ppm_setting': ['view', 'edit'],
            'comment': ['view', 'edit'],
        },
        'REQUESTER': {
            'work_order': ['view', 'edit'],
            'pending_ppm': ['view', 'edit'],
            'requisition': ['view', 'edit'],
            'ppm_setting': ['view', 'edit'],
            'comment': ['view', 'edit'],
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

        # Check if the role has the required permission for the feature
        required_action = 'edit' if request.method in ['POST', 'PUT', 'DELETE'] else 'view'
        return required_action in self.ROLE_FEATURES[user_role].get(feature, [])
    

class RoleBasedPermissionMixin:
    """Mixin for DRF ViewSets to apply role-based permissions"""
    permission_classes = [RoleBasedPermission]

    def get_permissions(self):
        return [permission() for permission in self.permission_classes]
