from django.db.models import TextChoices
from django.utils.translation import gettext as _


class PermissionEnum(TextChoices):
    view_users = "View users"
    create_users = "Create users"
    update_users = "Update users"
    delete_users = "Delete users"
    change_user_password = "Change user password"
    reset_user_password = "Reset user password"
    activate_user_account = "Activate user account"
    attach_or_detach_from_tenant = "Attach or detach user from tenant"

    view_roles = "View roles"
    create_roles = "Create roles"
    update_roles = "Update roles"
    delete_roles = "Delete roles"

    view_clients = "View clients"
    create_clients = "Create clients"
    update_clients = "Update clients"
    delete_clients = "Delete clients"
    activate_or_deactivate_clients = "Activate/Deactivate clients"

    manage_locations = "Manage locations"

    manage_documents = "Manage documents"

    view_reports = "View reports"


class RoleEnum(TextChoices):
    sysadmin = "Sysadmin"


PermissionGroups = {
    "User Management": [
        PermissionEnum.update_users,
        PermissionEnum.view_users,
        PermissionEnum.create_users,
        PermissionEnum.delete_users,
        PermissionEnum.change_user_password,
        PermissionEnum.reset_user_password,
        PermissionEnum.activate_user_account,
        PermissionEnum.attach_or_detach_from_tenant,
    ],
    "Roles Management": [
        PermissionEnum.view_roles,
        PermissionEnum.create_roles,
        PermissionEnum.update_roles,
        PermissionEnum.delete_roles,
    ],
    "Client Management": [
        PermissionEnum.view_clients,
        PermissionEnum.create_clients,
        PermissionEnum.update_clients,
        PermissionEnum.activate_or_deactivate_clients,
    ],
    "Others": [
        PermissionEnum.manage_documents,
        PermissionEnum.manage_locations,
        PermissionEnum.view_reports,
    ],
}
