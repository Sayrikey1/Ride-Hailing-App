from django.contrib.auth.mixins import AccessMixin
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.exceptions import APIException


class PermissionDenied(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = {"message": _("no.permission.for.action")}
    default_code = "permission_denied"


class AppAccessMixin(AccessMixin):
    def handle_no_permission(self):
        raise PermissionDenied()


class ActiveUserPermission(AppAccessMixin):
    def has_permission(self):
        if (
            not self.request.user.is_anonymous
            and self.request.user.deactivated_at is None
        ):
            return True

        return False

    def check_required_roles_and_permissions(self):
        if not self.has_permission():
            return self.handle_no_permission()


class CustomApiPermissionRequired(AppAccessMixin):
    """Verify that the current user has all specified permissions."""

    roles_required = None
    permission_required = None
    any_of_permission = None
    tenant = None
    user_type_required = None

    def is_required_user_type(self):
        user_type = self.user_type_required
        if not user_type:
            return True

        return (
            not self.request.user.is_anonymous
            and user_type == self.request.user.user_type
        )

    def get_permission_required(self):
        if self.permission_required:
            return self.permission_required

        return self.any_of_permission

    def has_permission(self):
        perms = self.get_permission_required()
        if not perms:
            return True

        return self.check_permission_list(self.request.user, perms)

    def has_roles(self):
        roles = self.roles_required
        if not roles:
            return True

        return self.check_role_list(self.request.user, roles)

    def check_permission_list(self, user, perms_list):
        if not user.is_anonymous and user.deactivated_at is not None:
            return False

        if not isinstance(perms_list, list):
            perms_list = [perms_list]

        for perm in perms_list:
            if user.has_permission(perm):
                return True

        return False

    def check_role_list(self, user, role_list):
        if not isinstance(role_list, list):
            role_list = [role_list]

        return user.has_any_of_roles(role_list)

    def check_required_roles_and_permissions(self, tenant=None):
        self.tenant = tenant
        if not self.is_required_user_type():
            return self.handle_no_permission()

        if not self.has_permission():
            return self.handle_no_permission()

        if not self.has_roles():
            return self.handle_no_permission()

    def dispatch(self, request, *args, **kwargs):
        if not self.is_required_user_type():
            raise PermissionDenied(_("invalid.user.type"))

        return super().dispatch(request, *args, **kwargs)
