from rest_framework import serializers
from accounts.models import User
from accounts.serializers.roles_permissions import SimpleRoleSerializer


class CreateUserSerializer(serializers.ModelSerializer):
    role_ids = serializers.ListSerializer(child=serializers.IntegerField())

    class Meta:
        model = User
        fields = ["username", "full_name", "phone_number", "email", "role_ids"]

#Get User Serializer. If user is a chef, return chef details too
class GetUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["username", "full_name", "phone_number", "email", "user_type", "roles", 
                  "status", "is_verified", "update_kyc_required","headline_title","about",
                  "followers_count", "following_count", "deals_joined", "created_at", "updated_at"]

class EditUserSerializer(serializers.ModelSerializer):
    role_ids = serializers.ListSerializer(child=serializers.IntegerField())
    class Meta:
        model = User
        fields = ["full_name", "phone_number", "email", "role_ids"]

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'username', 'full_name', 'headline_title', 'about'
        ]

    def update(self, instance, validated_data):
        # Optionally, perform custom logic before updating, if needed.
        
        # Update instance fields with validated data
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Save the updated instance
        instance.save()
        return instance

class UserListSerializer(serializers.ModelSerializer):
    roles = SimpleRoleSerializer(many=True)
    client_info = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "username",
            "full_name",
            "phone_number",
            "email",
            "roles",
            "user_type",
            "created_at",
            "updated_at",
        ]

class ActivateOrDeactivateUserSerializer(serializers.Serializer):
    is_active = serializers.BooleanField()
    reason = serializers.CharField(required=False, allow_blank=True, allow_null=True)

class FollowSerializer(serializers.Serializer):
    follower = serializers.UUIDField()
    following = serializers.UUIDField()

class CheckUsernameSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    count = serializers.IntegerField(required=False, min_value=1)
