"""Merge the two 0013 leaves: the OTP removal and the account backfill.

They touch different tables (``OtpCode`` vs ``CustomUser.account``), so the
merge needs no operations of its own — only a single leaf to migrate to.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0013_backfill_missing_accounts"),
        ("accounts", "0013_remove_otpcode_accounts_ot_user_id_ff054c_idx_and_more"),
    ]

    operations = []
