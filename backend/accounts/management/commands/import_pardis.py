"""Import a legacy Pardis SQLite database into this (trimmed SmartExchange) schema.

    python manage.py import_pardis /path/to/pardis.sqlite3 [--media-from DIR] [--dry-run]

The source file is opened read-only and never modified. Everything runs in one
transaction on the target; ``--dry-run`` rolls it back after verification.
Primary keys are preserved so foreign keys, price history ordering and the public
``/prices/live-json/`` output stay identical to the Pardis panel.
"""
import shutil
import sqlite3
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from accounts.models import Account
from accounts.plans import PLAN_GOLD
from core.encryption import encrypt_token

ACCOUNT_SLUG = "pardis"


class Importer:
    def __init__(self, src, cur, account_id, stdout):
        self.src = src
        self.cur = cur
        self.account_id = account_id
        self.out = stdout
        self.report = {}
        self.notes = []

    def rows(self, table):
        self.src.row_factory = sqlite3.Row
        return [dict(r) for r in self.src.execute(f'SELECT * FROM "{table}" ORDER BY id')]

    def insert(self, table, row):
        keys = list(row)
        self.cur.execute(
            f'INSERT INTO "{table}" ({",".join(chr(34) + k + chr(34) for k in keys)}) '
            f'VALUES ({",".join("%s" for _ in keys)})',
            [row[k] for k in keys],
        )

    def copy(self, table, *, extra=None, drop=(), transform=None, skip=None):
        """Copy every row (except those ``skip`` accepts), keeping only columns the target has."""
        target_cols = set(
            c.name for c in connection.introspection.get_table_description(self.cur, table)
        )
        count = 0
        for row in self.rows(table):
            if skip and skip(row):
                continue
            for d in drop:
                row.pop(d, None)
            if extra:
                row.update(extra(row) if callable(extra) else extra)
            if transform:
                row = transform(row)
            row = {k: v for k, v in row.items() if k in target_cols}
            self.insert(table, row)
            count += 1
        self.report[table] = count
        return count


def run_import(src_path, account_id, cur, stdout):
    src = sqlite3.connect(f"file:{src_path}?mode=ro", uri=True)
    imp = Importer(src, cur, account_id, stdout)
    acc = account_id

    # Users: Pardis gave every staff user full access with role="employee". SE
    # gates by role, so superusers become super_admin and other staff become
    # management (full operation inside the single Pardis account).
    def user_extra(row):
        is_super = bool(row["is_superuser"])
        return {
            "role": "super_admin" if is_super else "management",
            "token_version": 0, "country": "", "exchange_name": "", "first_name": "",
            "last_name": "", "phone": "", "telegram_id": "", "collaboration_type": "",
            "website": "", "sub_role": "admin", "telegram_username": "", "google_sub": "",
            "plan": PLAN_GOLD, "email": None,
            # Pardis has one desk: bind every user, super admins included, so what
            # they create belongs to it (an unbound super admin cannot write).
            "account_id": acc,
        }

    imp.copy("accounts_customuser", extra=user_extra)
    # SE seeds its own currency rows with different ids. Map Pardis ids to SE ids
    # by ISO code (adding any code SE lacks) and keep Pardis's names and symbols.
    cur_map = {}
    for c in imp.rows("category_currency"):
        cur.execute('SELECT id FROM "category_currency" WHERE code=%s', [c["code"]])
        found = cur.fetchone()
        if found:
            cur.execute('UPDATE "category_currency" SET name=%s, symbol=%s WHERE id=%s',
                        [c["name"], c["symbol"], found[0]])
            cur_map[c["id"]] = found[0]
        else:
            cur.execute('INSERT INTO "category_currency" (code, name, symbol) VALUES (%s,%s,%s)',
                        [c["code"], c["name"], c["symbol"]])
            cur_map[c["id"]] = cur.lastrowid
    imp.report["category_currency"] = len(cur_map)

    def remap_currencies(row):
        for k in ("source_currency_id", "target_currency_id"):
            if k in row:
                row[k] = cur_map[row[k]]
        return row
    imp.copy(
        "category_category",
        extra={"telegram_message_description": None, "telegram_media_url": "",
               "inline_buttons": "[]", "last_used_template_id": None, "account_id": acc},
    )

    # Pardis listed price types by name; SE sorts by (order, id). Rank by name per
    # category so every list keeps the Pardis order.
    ptypes = imp.rows("category_pricetype")
    rank = {}
    for cat_id in {p["category_id"] for p in ptypes}:
        for i, p in enumerate(sorted((p for p in ptypes if p["category_id"] == cat_id), key=lambda p: p["name"])):
            rank[p["id"]] = i
    # An empty price type that repeats a populated one from another category is a
    # misplaced duplicate (Pardis had a second, never-priced "لیر" under Pound).
    src.row_factory = sqlite3.Row
    history_counts = {
        r["price_type_id"]: r["n"]
        for r in src.execute("SELECT price_type_id, COUNT(*) AS n FROM change_price_pricehistory GROUP BY price_type_id")
    }

    def pair_key(p):
        return (p["source_currency_id"], p["target_currency_id"], p["trade_type"])

    def misplaced_duplicate(p):
        return history_counts.get(p["id"], 0) == 0 and any(
            q["category_id"] != p["category_id"]
            and history_counts.get(q["id"], 0) > 0
            and pair_key(q) == pair_key(p)
            for q in ptypes
        )

    for p in ptypes:
        if misplaced_duplicate(p):
            imp.notes.append(
                f"price type {p['id']} ({p['name']}) in category {p['category_id']} skipped: "
                "empty duplicate of a priced type in another category"
            )
    imp.copy("category_pricetype", extra=lambda r: {"is_active": 1, "order": rank[r["id"]]},
             transform=remap_currencies, skip=misplaced_duplicate)
    imp.copy("change_price_pricehistory", extra={"event_at": None})

    # Special prices: keep one row per entry (cash/account columns preserved); SE
    # additionally needs one pair per type that every history row points at.
    imp.copy(
        "special_price_specialpricetype",
        extra={"icon": None, "last_used_template_id": None, "account_id": acc},
        transform=remap_currencies,
    )
    now = timezone.now().isoformat(sep=" ")
    pair_of = {}
    for t in imp.rows("special_price_specialpricetype"):
        cur.execute(
            'INSERT INTO "special_price_specialpricepair" '
            "(special_price_type_id, name, source_currency_id, target_currency_id, trade_type, created_at, updated_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s)",
            [t["id"], t["name"], cur_map[t["source_currency_id"]], cur_map[t["target_currency_id"]], t["trade_type"], now, now],
        )
        pair_of[t["id"]] = cur.lastrowid
    imp.report["special_price_specialpricepair"] = len(pair_of)
    imp.copy(
        "special_price_specialpricehistory",
        extra=lambda r: {"pair_id": pair_of[r["special_price_type_id"]], "event_at": None},
    )

    imp.copy("telegram_app_telegrambot", extra=lambda r: {
        "token": encrypt_token(r["token"]), "display_name": "", "notes": "",
        "restrict_to_known_channels": 0, "log_all_messages": 0,
        "default_exchange_ttl_minutes": 5, "owner_id": None, "account_id": acc,
    })
    imp.copy("telegram_app_telegramchannel", extra={
        "bot_admin_verified": 0, "last_member_count": None, "last_member_sampled_at": None})
    imp.copy("telegram_app_defaultmessagesettings")

    imp.copy("price_publisher_pricetemplate", extra={"account_id": acc, "plan": PLAN_GOLD})
    imp.copy("setting_pricethemestate")
    imp.copy("setting_log", extra={"account_id": acc})

    # Template editor: SE requires a category and has no per-special-price link.
    # Templates bound only to a special price type get the category whose price
    # type matches that special type (SE's own matching rule) and are marked
    # inactive so they never enter category round-robin; the original binding is
    # recorded in the import report.
    types = {t["id"]: t for t in imp.rows("special_price_specialpricetype")}

    def template_fix(row):
        row = dict(row)
        if row.get("category_id") is None:
            spt = types.get(row.get("special_price_type_id"))
            cat = None
            if spt:
                cur.execute(
                    'SELECT category_id FROM "category_pricetype" WHERE source_currency_id=%s '
                    "AND target_currency_id=%s AND trade_type=%s ORDER BY category_id, id LIMIT 1",
                    [cur_map[spt["source_currency_id"]], cur_map[spt["target_currency_id"]], spt["trade_type"]],
                )
                found = cur.fetchone()
                cat = found[0] if found else None
            if cat is None:
                cur.execute('SELECT id FROM "category_category" ORDER BY id LIMIT 1')
                cat = cur.fetchone()[0]
            row["category_id"] = cat
            row["is_active"] = 0
            imp.notes.append(
                f"template {row['id']} ({row['name']}) was bound to special price type "
                f"{row.get('special_price_type_id')}; imported under category {cat}, inactive"
            )
        return row

    imp.copy(
        "template_editor_template",
        extra={"canvas_width": 1920, "canvas_height": 1080, "config_json": "{}",
               "orientation": "landscape", "is_active": 1, "publish_order": 0,
               "telegram_caption_template": "", "telegram_buttons_json": "[]",
               "account_id": acc, "plan": PLAN_GOLD},
        transform=template_fix,
    )

    imp.copy("finalize_finalization")
    imp.copy("finalize_finalizedpricehistory")
    imp.copy("finalize_specialpricefinalization")
    src.close()
    return imp


class Command(BaseCommand):
    help = "Import a legacy Pardis SQLite database into the current database."

    def add_arguments(self, parser):
        parser.add_argument("source", help="Path to the Pardis db.sqlite3 (opened read-only)")
        parser.add_argument("--media-from", help="Pardis public/media dir to copy into MEDIA_ROOT")
        parser.add_argument("--dry-run", action="store_true", help="Verify, then roll back")

    def handle(self, *args, source, media_from=None, dry_run=False, **opts):
        src_path = Path(source).resolve()
        if not src_path.is_file():
            raise CommandError(f"{src_path} not found")
        if Account.objects.filter(slug=ACCOUNT_SLUG).exists():
            raise CommandError("Pardis account already exists; refusing to import twice.")

        with transaction.atomic():
            account = Account.objects.create(name="Pardis", slug=ACCOUNT_SLUG, is_paid=True)
            with connection.cursor() as cur:
                imp = run_import(str(src_path), account.pk, cur, self.stdout)
                cur.execute("PRAGMA foreign_key_check")
                broken = cur.fetchall()
            if broken:
                raise CommandError(f"foreign key violations after import: {broken[:5]}")
            for table, n in imp.report.items():
                self.stdout.write(f"{table}: {n}")
            for note in imp.notes:
                self.stdout.write(f"NOTE {note}")
            if dry_run:
                transaction.set_rollback(True)
                self.stdout.write("dry run: rolled back")
                return

        if media_from:
            src_media = Path(media_from)
            if not src_media.is_dir():
                raise CommandError(f"{src_media} is not a directory")
            copied = 0
            for f in src_media.rglob("*"):
                if f.is_file() and f.name != ".DS_Store":
                    dest = Path(settings.MEDIA_ROOT) / f.relative_to(src_media)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    # The live Pardis files win over anything the repo ships.
                    if not dest.exists() or dest.read_bytes() != f.read_bytes():
                        shutil.copy2(f, dest)
                        copied += 1
            self.stdout.write(f"media files copied: {copied}")
        from accounts.management.commands.apply_pardis_branding import (
            apply_branding,
            apply_telegram_content,
        )

        apply_branding(account)
        apply_telegram_content(account)
        self.stdout.write(self.style.SUCCESS("Pardis import complete."))
