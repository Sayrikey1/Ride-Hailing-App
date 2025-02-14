import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q, TextChoices

from accounts.constants.roles_permissions import RoleEnum
from crm.models import BaseModel

class UserTypes(TextChoices):
    driver = "Driver"
    customer = "Customer"
    admin = "Admin"


class ActiveStatus(TextChoices):
    Active = "Active"
    Inactive = "Inactive"


class PasswordResetRequestStatus(TextChoices):
    available = "Available"
    expired = "Expired"


class User(AbstractUser, BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=60, unique=True)
    full_name = models.CharField(max_length=255)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(unique=True, null=False, blank=False)
    phone_number = models.CharField(max_length=70, null=True, blank=True)
    user_type = models.CharField(
        max_length=255, default=UserTypes.customer, choices=UserTypes.choices
    )
    is_verified = models.BooleanField(default=False)
    gender = models.CharField(max_length=10, blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    country = models.CharField(max_length=100)
    registration_complete = models.BooleanField(default=False)
    update_kyc_required = models.BooleanField(default=True)
    fcm_token = models.TextField(null=True, blank=True)
    devices = models.JSONField(default=list)
    address = models.CharField(
        max_length=300, null=True, blank=True
    ) 
    address_coord = models.JSONField(null=True, blank=True)
    status = models.CharField(
        max_length=50, default="active"
    )  # Adjust the field type and length as needed

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    roles = models.ManyToManyField("Role", related_query_name="roles", blank=True)

    groups = None
    user_permissions = None

    def save(self, *args, **kwargs):
        """
        Overrides the save method to split `full_name` into `first_name` and `last_name`.
        """
        if self.full_name:
            # Split the full_name into first_name and last_name
            parts = self.full_name.strip().split(" ", 1)  # Split into two parts only
            self.first_name = parts[0]
            self.last_name = parts[1] if len(parts) > 1 else ""  # Default to empty if no last name

        super().save(*args, **kwargs)  # Call the parent class's save method

    def natural_key(self):
        return self.username

    def has_permission(self, perm_name):
        """Check if the user has a specific permission"""
        if self.is_superuser:
            return True
        return self.roles.filter(
            Q(permissions__name=perm_name) | Q(name__exact=RoleEnum.sysadmin)
        ).exists()

    def has_role(self, role_name):
        """Check if the user has a specific role."""
        return self.roles.filter(
            Q(name=role_name) | Q(name__exact=RoleEnum.sysadmin)
        ).exists()

    def has_any_of_roles(self, role_names):
        """Check if the user has any of a list of roles."""
        return self.roles.filter(
            Q(name__in=role_names) | Q(name__exact=RoleEnum.sysadmin)
        ).exists()

    def __str__(self):
        return self.get_full_name() + f" ({self.username})"


class RegisterLog(BaseModel):
    email = models.EmailField(unique=True, null=False)
    payload = models.JSONField()
    otp = models.CharField(max_length=255, null=False)
    otp_requested_at = models.DateTimeField(null=False)
    is_verified = models.BooleanField(default=False)
    otp_verified_at = models.DateTimeField(null=True)

    def __str__(self):
        return self.email


class Permission(models.Model):
    name = models.CharField(max_length=255, unique=True)
    group_name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Role(models.Model):
    name = models.CharField(max_length=255, null=True)
    description = models.TextField(null=True, blank=True)
    permissions = models.ManyToManyField(
        Permission, blank=True, db_table="role_permissions"
    )
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class PasswordResetRequest(BaseModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=False,
        related_name="password_reset_request",
    )
    otp = models.CharField(max_length=255, null=True)
    status = models.CharField(
        max_length=255,
        choices=PasswordResetRequestStatus.choices,
        default=PasswordResetRequestStatus.available,
    )

