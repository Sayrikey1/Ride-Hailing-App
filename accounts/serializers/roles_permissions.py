from rest_framework import serializers

from accounts.models import Permission


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["id", "name", "group_name"]


class CreateEditRoleSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    description = serializers.CharField(required=True)
    permission_ids = serializers.ListField(child=serializers.IntegerField())


class SimpleRoleSerializer(serializers.Serializer):
    id = serializers.CharField(required=True)
    name = serializers.CharField(required=True)
    description = serializers.CharField(required=True)
    permissions = PermissionSerializer(many=True)


class RoleSerializer(SimpleRoleSerializer):
    permissions = PermissionSerializer(many=True)
