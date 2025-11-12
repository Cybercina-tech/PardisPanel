from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils import timezone
from .managers import CustomUserManager


class CustomUser(AbstractBaseUser, PermissionsMixin):
    ROLE_MANAGEMENT = 'management'
    ROLE_EMPLOYEE = 'employee'
    ROLE_DEVELOPER = 'developer'

    ROLE_CHOICES = (
        (ROLE_MANAGEMENT, 'Management'),
        (ROLE_EMPLOYEE, 'Employee'),
        (ROLE_DEVELOPER, 'Developer'),
    )

    username = models.CharField(max_length=150, unique=True)
    full_name = models.CharField(max_length=255, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_EMPLOYEE)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = CustomUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'

    def get_full_name(self):
        return self.full_name or self.username

    def get_short_name(self):
        return self.username

    def __str__(self):
        return self.get_full_name()
