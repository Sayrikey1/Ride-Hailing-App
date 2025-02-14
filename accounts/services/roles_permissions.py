from typing import Any

from django.db.models import Q
from django.utils import timezone

from accounts.constants.roles_permissions import PermissionGroups, RoleEnum
from accounts.models import Permission, Role
from accounts.serializers.roles_permissions import PermissionSerializer, RoleSerializer
from core.errors.app_errors import OperationError
from crm.constants import ActivityType
from services.util import CustomAPIRequestUtil


class PermissionService(CustomAPIRequestUtil):
    @staticmethod
    def create_default_permissions():
        permission_ids = []
        for group, permissions in PermissionGroups.items():
            for permission in permissions:
                permission_obj, is_created = Permission.objects.update_or_create(
                    name=permission, defaults={"group_name": group}
                )
                permission_ids.append(permission_obj.pk)
                print(
                    f"Permission '{permission_obj}'",
                    "created" if is_created else "updated",
                )

        Permission.objects.exclude(pk__in=permission_ids).delete()

    @classmethod
    def get_permissions_by_ids(cls, permission_ids):
        return Permission.objects.filter(pk__in=permission_ids)

    @classmethod
    def get_permissions_by_names(cls, permission_names):
        return Permission.objects.filter(name__in=permission_names)

    @classmethod
    def get_permission_by_id(cls, permission_id):
        return Permission.objects.filter(pk=permission_id)

    @classmethod
    def get_permission_by_name(cls, permission_name):
        return Permission.objects.filter(name=permission_name)

    def fetch_permissions(self, filter_params) -> (Any, OperationError):
        filter_keyword = filter_params.get("keyword")
        self.page_size = filter_params.get("page_size", 100)

        q = Q()
        if filter_keyword:
            q = Q(name__icontains=filter_keyword)

        queryset = Permission.objects.filter(q)
        page = self.paginate_queryset(queryset, request=self.request)
        data = PermissionSerializer(page, many=True).data

        return self.get_paginated_list_response(data, queryset.count())


class RoleService(CustomAPIRequestUtil):
    @staticmethod
    def create_default_roles():
        role, is_created = Role.objects.update_or_create(
            name=RoleEnum.sysadmin, defaults={"description": "Tenant/System admin"}
        )
        print(role, f"has been {'created' if is_created else 'updated'}")

    def create(self, payload):
        permission_service = PermissionService(self.request)
        permissions = permission_service.get_permissions_by_ids(
            payload.get("permission_ids")
        )
        name = payload.get("name")
        description = payload.get("description")
        tenant = self.auth_tenant
        if not tenant:
            return None, self.make_error("Invalid tenant specified")

        role, is_created = Role.objects.get_or_create(
            name=name, defaults={"description": description}
        )

        if not is_created:
            return None, self.make_error(f"Role '{name}' already exists")

        role.permissions.add(*permissions)
        role.save()
        self.report_activity(ActivityType.create, role)

        return role, None

    def delete(self, role_id):
        role, error = self.fetch_single(role_id)
        if error:
            return None, error

        role.deleted_at = timezone.now()
        role.deleted_by = self.auth_user
        role.save()

        cache_key = self.generate_cache_key("role_id", role.id)
        self.clear_cache(cache_key)

        self.report_activity(ActivityType.delete, role)

        return role, None

    @classmethod
    def check_if_role_exists(cls, new_role_name, existing_role_id):
        return (
            Role.objects.filter(name=new_role_name)
            .exclude(id=existing_role_id)
            .exists()
        )

    def update(self, payload, role_id):
        role, error = self.fetch_single(role_id)
        if error:
            return None, error

        permission_service = PermissionService(self.request)
        permissions = permission_service.get_permissions_by_ids(
            payload.get("permission_ids")
        )

        name = payload.get("name")
        if self.check_if_role_exists(name, role_id):
            return None, self.make_400("Role with name already exists")
        role.name = name
        role.description = payload.get("description")
        role.permissions.clear()
        role.permissions.add(*permissions)
        role.save()
        self.report_activity(ActivityType.update, role)

        cache_key = self.generate_cache_key("role_id", role_id)
        self.clear_cache(cache_key)

        return role, None

    def fetch_single(self, role_id, tenant=None):
        def fetch():
            role = (
                Role.available_objects.prefetch_related("permissions")
                .filter(pk=role_id)
                .first()
            )

            if not role:
                return None, "Role not found"
            return role, None

        cache_key = self.generate_cache_key("role_id", role_id)
        return self.get_cache_value_or_default(cache_key, fetch)

    @classmethod
    def fetch_by_ids(cls, role_ids):
        return Role.available_objects.filter(pk__in=role_ids)

    def fetch_list(self, filter_params) -> (Any, OperationError):
        filter_keyword = filter_params.get("keyword")
        self.page_size = filter_params.get("page_size", 100)

        q = Q()
        if filter_keyword:
            q = Q(name__icontains=filter_keyword) | Q(
                description__icontains=filter_keyword
            )

        queryset = Role.available_objects.prefetch_related("permissions").filter(q)
        page = self.paginate_queryset(queryset, request=self.request)
        data = RoleSerializer(page, many=True).data

        return self.get_paginated_list_response(data, queryset.count())
