#!/usr/bin/env bash
# Deploy the Pardis panel on cPanel/Passenger next to a running legacy panel.
#
#   cpanel_deploy.sh prepare   build venv + code + env file; rehearse the import on a scratch DB.
#                              Touches nothing the live panel uses.
#   cpanel_deploy.sh cutover   re-import a fresh copy of the live DB, then point the panel
#                              domain's Passenger block at the new app (old .htaccess is backed up).
#   cpanel_deploy.sh rollback  restore the backed-up .htaccess and restart.
#
# Layout (all under $HOME, outside every web root):
#   $APP/repo            git checkout      $APP/.env.production   secrets (chmod 600)
#   $APP/data            new SQLite DB     $HOME/virtualenv/PardisPanelNew/3.12   venv
set -euo pipefail

APP="${APP:-$HOME/PardisPanelNew}"
REPO_URL="${REPO_URL:-https://github.com/Cybercina-tech/PardisPanel.git}"
BRANCH="${BRANCH:-main}"
VENV="${VENV:-$HOME/virtualenv/PardisPanelNew/3.12}"
OLD_ROOT="${OLD_ROOT:-$HOME/SarafiPardis}"            # legacy docroot + Passenger .htaccess
OLD_DB="${OLD_DB:-$OLD_ROOT/public/db.sqlite3}"
OLD_MEDIA="${OLD_MEDIA:-$OLD_ROOT/public/public/media}"
OLD_SETTINGS="${OLD_SETTINGS:-$OLD_ROOT/public/SarafiPardis/settings.py}"
HOST="${HOST:-panel.sarafipardis.co.uk}"
BACKEND="$APP/repo/backend"
ENVFILE="$APP/.env.production"

log() { printf '\n== %s\n' "$*"; }

find_python() {
  for c in /opt/alt/python312/bin/python3.12 \
           "$(readlink -f "$HOME/virtualenv/SarafiPardis/3.12/bin/python" 2>/dev/null || true)" \
           "$(command -v python3.12 || true)"; do
    if [ -n "$c" ] && [ -x "$c" ]; then echo "$c"; return; fi
  done
  echo "no python3.12 found" >&2; exit 1
}

load_env() { set -a; . "$ENVFILE"; set +a; }
manage() { (cd "$BACKEND" && "$VENV/bin/python" manage.py "$@"); }

write_env() {
  [ -f "$ENVFILE" ] && { echo "env file exists, keeping it"; return; }
  umask 077
  secret="$("$VENV/bin/python" -c 'import secrets;print(secrets.token_urlsafe(64))')"
  # Same key the legacy panel pushes with, copied server-side and never printed.
  ext=""
  if [ -f "$OLD_SETTINGS" ]; then
    ext="$(grep -E "^\s*EXTERNAL_API_KEY\s*=\s*['\"]" "$OLD_SETTINGS" | head -1 | sed -E "s/.*=\s*['\"]([^'\"]*)['\"].*/\1/" || true)"
  fi
  {
    echo "DJANGO_SECRET_KEY=$secret"
    echo "DJANGO_DEBUG=False"
    echo "DJANGO_ALLOWED_HOSTS=$HOST,www.$HOST"
    echo "DJANGO_CSRF_TRUSTED_ORIGINS=https://$HOST"
    echo "SQLITE_PATH=$APP/data/db.sqlite3"
    echo "EXTERNAL_API_KEY=$ext"
  } > "$ENVFILE"
  chmod 600 "$ENVFILE"
  echo "env file written (EXTERNAL_API_KEY $([ -n "$ext" ] && echo found || echo NOT found — set it by hand))"
}

prepare() {
  mkdir -p "$APP/data"
  log "code"
  if [ -d "$APP/repo/.git" ]; then git -C "$APP/repo" fetch -q origin "$BRANCH" && git -C "$APP/repo" reset -q --hard "origin/$BRANCH"
  else git clone -q --depth 1 --branch "$BRANCH" "$REPO_URL" "$APP/repo"; fi
  git -C "$APP/repo" log --oneline | head -1

  log "virtualenv"
  if [ ! -x "$VENV/bin/python" ]; then
    mkdir -p "$(dirname "$VENV")"
    "$(find_python)" -m venv "$VENV"
  fi
  "$VENV/bin/python" --version
  "$VENV/bin/pip" install -q --upgrade pip
  "$VENV/bin/pip" install -q -r "$BACKEND/requirements.txt"

  log "env file"
  write_env
  load_env

  log "rehearsal import on a scratch DB (live DB opened read-only)"
  export SQLITE_PATH="$APP/data/rehearsal.sqlite3"
  rm -f "$SQLITE_PATH"
  manage migrate --noinput | tail -2
  manage import_pardis "$OLD_DB" --media-from "$OLD_MEDIA" --dry-run | tail -40
  rm -f "$SQLITE_PATH"
  manage check || true
  log "prepare done"
}

cutover() {
  load_env
  [ -d "$BACKEND" ] || { echo "run prepare first" >&2; exit 1; }
  log "fresh DB from a copy of the live DB"
  export SQLITE_PATH="$APP/data/db.sqlite3"
  [ -f "$SQLITE_PATH" ] && mv "$SQLITE_PATH" "$SQLITE_PATH.$(date +%Y%m%d%H%M%S).bak"
  cp "$OLD_DB" "$APP/data/legacy_snapshot.sqlite3"
  manage migrate --noinput | tail -2
  manage import_pardis "$APP/data/legacy_snapshot.sqlite3" --media-from "$OLD_MEDIA" | tail -40
  manage collectstatic --noinput | tail -1

  log "smoke test before switching"
  (cd "$BACKEND" && "$VENV/bin/python" - <<'PY'
import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MrExchangePanel.settings")
django.setup()
from django.test import Client
c = Client(HTTP_HOST=os.environ.get("HOST_HDR", "panel.sarafipardis.co.uk"))
for url in ("/prices/live-json/", "/api/health/", "/"):
    r = c.get(url, secure=True)
    print(url, r.status_code, len(r.content))
PY
  )

  log "switch Passenger"
  HT="$OLD_ROOT/.htaccess"
  [ -f "$HT.pre-pardis-spa" ] || cp -p "$HT" "$HT.pre-pardis-spa"
  sed -i -E "s#^PassengerAppRoot .*#PassengerAppRoot \"$BACKEND\"#; s#^PassengerPython .*#PassengerPython \"$VENV/bin/python\"#" "$HT"
  mkdir -p "$BACKEND/tmp" && touch "$BACKEND/tmp/restart.txt"
  grep -n '^Passenger' "$HT"
  log "cutover done — rollback: cpanel_deploy.sh rollback"
}

rollback() {
  HT="$OLD_ROOT/.htaccess"
  [ -f "$HT.pre-pardis-spa" ] || { echo "no backup found" >&2; exit 1; }
  cp -p "$HT.pre-pardis-spa" "$HT"
  mkdir -p "$OLD_ROOT/tmp" && touch "$OLD_ROOT/tmp/restart.txt"
  log "rolled back"; grep -n '^Passenger' "$HT"
}

case "${1:-}" in
  prepare) prepare ;;
  cutover) cutover ;;
  rollback) rollback ;;
  *) echo "usage: $0 prepare|cutover|rollback" >&2; exit 2 ;;
esac
