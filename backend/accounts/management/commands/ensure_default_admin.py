import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = (
        "Create default admin user if missing (username/password from args or env). "
        "If the user already exists, staff/superuser/role are fixed; set "
        "DEFAULT_ADMIN_SYNC_PASSWORD=true to also reset the password from env/CLI."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            default=os.environ.get("DEFAULT_ADMIN_USERNAME", "admin"),
        )
        parser.add_argument(
            "--password",
            default=os.environ.get("DEFAULT_ADMIN_PASSWORD", "admin"),
        )

    def handle(self, *args, **options):
        # Strip CR/LF/spaces from env-file values (Windows CRLF often breaks password matching).
        username = (str(options["username"] or "")).strip().replace("\r", "")
        password = (str(options["password"] or "")).strip().replace("\r", "")
        if not username:
            username = "admin"
        if not password:
            password = "admin"
        sync_password = os.environ.get("DEFAULT_ADMIN_SYNC_PASSWORD", "").strip().lower() in (
            "true",
            "1",
            "yes",
        )

        user = User.objects.filter(username=username).first()
        if user:
            updated = False
            if not user.is_staff:
                user.is_staff = True
                updated = True
            if not user.is_superuser:
                user.is_superuser = True
                updated = True
            if user.role != User.ROLE_SUPER_ADMIN:
                user.role = User.ROLE_SUPER_ADMIN
                updated = True
            if sync_password:
                user.set_password(password)
                updated = True
            if updated:
                user.save()
                if sync_password:
                    self.stdout.write(
                        self.style.WARNING(
                            f'User "{username}" updated (including password sync from env/DEFAULT_ADMIN_*).'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'User "{username}" already existed; updated staff/superuser/role to full admin.'
                        )
                    )
            else:
                self.stdout.write(
                    self.style.NOTICE(
                        f'User "{username}" already exists; password left unchanged. '
                        f'Set DEFAULT_ADMIN_SYNC_PASSWORD=true to reset password to match DEFAULT_ADMIN_PASSWORD.'
                    )
                )
            return

        User.objects.create_superuser(
            username=username,
            password=password,
            role=User.ROLE_SUPER_ADMIN,
            full_name="Administrator",
        )
        self.stdout.write(self.style.SUCCESS(f'Created superuser "{username}" with role super_admin.'))
