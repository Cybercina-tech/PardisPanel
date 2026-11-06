#!/usr/bin/env python3
"""Record the tutorial GIFs by driving the running dev app.

These clips are what the landing page and the tutorial hub show instead of the
42 MB demo video that used to sit there, so size discipline is the point:
Playwright records WebM, ffmpeg palettes it down to a GIF no wider than 900 px,
and each flow is trimmed to the seconds that actually show something.

One flow per tutorial in ``frontend/src/content/tutorials/index.js``, named
after its slug, because the post names the file it ships with. Adding a
tutorial means adding a flow here and re-recording — a post whose clip shows an
older build is worse than a post with no clip.

Run against a dev stack that is already up (``./dev.sh up``) and seeded::

    python scripts/record_gifs.py --password 'Tutorial!2026'
    python scripts/record_gifs.py --only publish-prices

Playwright and ffmpeg live on the host, not in the container — install once
with ``pip install playwright && playwright install chromium``.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "backend" / "static" / "landing" / "gifs"

BASE_URL = "http://localhost:5252"
VIEWPORT = {"width": 1440, "height": 900}
GIF_WIDTH = 900
GIF_FPS = 8

DEFAULT_USER = "demo.owner"


def _settle(page: Page, seconds: float = 1.2) -> None:
    """Hold the frame. Playback needs the pause to be readable."""
    page.wait_for_timeout(int(seconds * 1000))


def _click_nav(page: Page, href: str) -> None:
    """Follow a sidebar link, then let the view finish painting."""
    page.click(f'a[href="{href}"]')
    page.wait_for_load_state("networkidle")
    _settle(page)


def login(page: Page, username: str, password: str) -> None:
    page.goto(f"{BASE_URL}/login", wait_until="networkidle")
    page.fill('input[autocomplete="username"]', username)
    page.fill('input[type="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_url(f"{BASE_URL}/**", timeout=30_000)
    page.wait_for_load_state("networkidle")
    _settle(page, 2)
    _dismiss_chrome(page)
    _dismiss_tour(page)


def _dismiss_chrome(page: Page) -> None:
    """Close the PWA install prompt, which otherwise sits over every clip."""
    later = page.get_by_role("button", name="Later")
    if later.count():
        later.first.click()
        _settle(page, 0.6)


def _dismiss_tour(page: Page) -> None:
    """Close the onboarding tour if this account has not seen it.

    It opens over the panel on a first sign-in, which is exactly what the
    signup clip is for and exactly what the other three must not show.
    """
    close = page.locator(".onboarding-tour__close")
    if close.count():
        close.first.click()
        _settle(page, 1)


def flow_publish_prices(page: Page) -> None:
    """Update prices -> finalize -> publish."""
    _click_nav(page, "/update")
    _settle(page, 2)

    for value, field in zip(("66500", "67200"), page.locator('input[type="number"]').all()[:2]):
        field.click()
        field.fill(value)
        _settle(page, 0.8)

    _click_nav(page, "/finalize")
    _settle(page, 3)


def flow_template_editor(page: Page) -> None:
    """Template editor: open a template, add widgets, bind one to a price.

    The widget library's buttons are a flat list in which the first entry is a
    group *header*, not a widget — clicking blindly down that list collapses
    the group and adds nothing, which is how this clip once ended up showing
    an empty canvas. Widgets are matched by their accessible name instead.
    """
    _click_nav(page, "/templates")
    _settle(page, 2.5)

    card = page.locator('a[href^="/templates/"][href$="/editor"]')
    if not card.count():
        raise RuntimeError("No template to record. Create one in the panel first.")
    card.first.click()
    page.wait_for_load_state("networkidle")
    _settle(page, 3)

    library = page.locator('aside:has-text("Widget library")').first

    for name in (r"^Text", r"^Date"):
        widget = library.get_by_role("button", name=re.compile(name))
        if widget.count():
            widget.first.click()
            _settle(page, 1.6)

    # Binding a widget to a live price is the step the post is actually about,
    # and its group starts collapsed — the buttons are in the DOM but not on
    # screen, so the header has to be opened before any of them can be clicked.
    group = library.get_by_role("button", name="Price bindings")
    if group.count():
        group.first.click()
        _settle(page, 1.2)

    binding = library.locator("button.btn-luxury-outline").first
    if binding.count() and binding.is_visible():
        binding.click()
        _settle(page, 2)

    _settle(page, 2)


def flow_telegram_bot(page: Page) -> None:
    """Telegram: the form a bot token is pasted into, and what it configures.

    Deliberately the New Bot page rather than the hub. The hub verifies the
    selected bot against Telegram on load, and the seeded demo bot carries an
    invalid token on purpose so that nothing in a dev stack can ever reach a
    real channel — so the hub greets this clip with a rejection banner, which
    is the last thing a post called "connect your bot" should open on.

    Nothing is submitted: the token below is not a token, and a real one would
    not belong in a recording script anyway.
    """
    _click_nav(page, "/telegram")
    _settle(page, 1.5)
    page.goto(f"{BASE_URL}/telegram/bots/new", wait_until="networkidle")
    _settle(page, 2.5)

    name_field = page.get_by_placeholder("e.g. MyExchangeRatesBot")
    if name_field.count():
        name_field.first.click()
        name_field.first.type("MyExchangeRatesBot", delay=70)
        _settle(page, 1.2)

    token_field = page.get_by_placeholder("Paste token from BotFather")
    if token_field.count():
        token_field.first.click()
        token_field.first.type("8100000000:AA-ExampleTokenFromBotFather", delay=45)
        _settle(page, 1.8)

    # The options below the token are the "choose what gets posted" step.
    page.mouse.wheel(0, 320)
    _settle(page, 2.5)
    page.mouse.wheel(0, 320)
    _settle(page, 2.5)


def flow_signup_tour(page: Page, username: str, password: str) -> None:
    """Signup form -> the confirmation code screen -> the first-login tour.

    The form is shown but not submitted: a real submission would burn a
    one-time code and leave a junk account behind on every re-record. The tour
    is replayed from the header instead, which is the same component a new
    customer meets.
    """
    page.goto(f"{BASE_URL}/signup", wait_until="networkidle")
    _settle(page, 2.5)
    page.mouse.wheel(0, 300)
    _settle(page, 2)

    page.goto(f"{BASE_URL}/confirm", wait_until="networkidle")
    _settle(page, 3)

    login(page, username, password)
    page.click('button[aria-label*="tour" i], button[title*="tour" i]')
    _settle(page, 2.5)
    for _ in range(3):
        page.click(".onboarding-tour__btn--primary")
        _settle(page, 2)


def flow_customer_website(page: Page) -> None:
    """The website builder: a layout, a section, the live preview."""
    _click_nav(page, "/website")
    _settle(page, 3)

    # The section list is the left rail of the builder; opening one is what
    # shows that the content is edited in place rather than in a form far away.
    section = page.locator('[data-section-row], aside button, aside [role="button"]').first
    if section.count():
        section.click()
        _settle(page, 2)

    page.mouse.wheel(0, 500)
    _settle(page, 2.5)
    page.mouse.wheel(0, 500)
    _settle(page, 2)


def flow_customers_hub(page: Page) -> None:
    """Customers: the list, then one customer's channels and history."""
    _click_nav(page, "/customers")
    _settle(page, 3)

    row = page.locator('table tbody tr, [data-customer-row]').first
    if row.count():
        row.click()
        page.wait_for_load_state("networkidle")
        _settle(page, 3)
        page.mouse.wheel(0, 400)
        _settle(page, 2.5)


def flow_campaigns_vip(page: Page) -> None:
    """Campaigns: the list, then the form that defines a benefit."""
    _click_nav(page, "/campaigns")
    _settle(page, 3)

    new_campaign = page.get_by_role("button", name="New").or_(
        page.get_by_role("button", name="Create")
    )
    if new_campaign.count():
        new_campaign.first.click()
        _settle(page, 2.5)
        page.mouse.wheel(0, 300)
        _settle(page, 2)
    else:
        page.mouse.wheel(0, 400)
        _settle(page, 2.5)


FLOWS = {
    "publish-prices": (flow_publish_prices, True),
    "template-editor": (flow_template_editor, True),
    "telegram-bot": (flow_telegram_bot, True),
    "customer-website": (flow_customer_website, True),
    "customers-hub": (flow_customers_hub, True),
    "campaigns-vip": (flow_campaigns_vip, True),
    "signup-tour": (flow_signup_tour, False),
}


def to_gif(webm: Path, gif: Path) -> None:
    """WebM -> palette-optimised GIF.

    Two passes: ffmpeg builds a palette from the whole clip first, because a
    per-frame palette is what makes screen recordings band and dither.
    """
    with tempfile.TemporaryDirectory() as tmp:
        palette = Path(tmp) / "palette.png"
        scale = f"fps={GIF_FPS},scale={GIF_WIDTH}:-1:flags=lanczos"
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(webm),
             "-vf", f"{scale},palettegen=stats_mode=diff", str(palette)],
            check=True,
        )
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(webm), "-i", str(palette),
             "-lavfi", f"{scale}[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=3",
             "-loop", "0", str(gif)],
            check=True,
        )


def record(name: str, needs_login: bool, username: str, password: str) -> None:
    flow, _ = FLOWS[name]
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(
            viewport=VIEWPORT,
            record_video_dir=tmp,
            record_video_size=VIEWPORT,
        )
        page = context.new_page()
        try:
            if needs_login:
                login(page, username, password)
                flow(page)
            else:
                flow(page, username, password)
            _settle(page, 1.5)
        finally:
            video = page.video
            context.close()
            browser.close()

        webm = Path(video.path())
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        gif = OUTPUT_DIR / f"{name}.gif"
        to_gif(webm, gif)
        size_mb = gif.stat().st_size / 1_048_576
        print(f"{gif.relative_to(REPO_ROOT)} — {size_mb:.1f} MB")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user", default=DEFAULT_USER, help="Panel account to record with")
    parser.add_argument("--password", required=True, help="Its password")
    parser.add_argument("--only", action="append", choices=sorted(FLOWS), help="Record just this flow")
    args = parser.parse_args()

    if shutil.which("ffmpeg") is None:
        print("ffmpeg is not on PATH.", file=sys.stderr)
        return 1

    for name in args.only or sorted(FLOWS):
        _, needs_login = FLOWS[name]
        record(name, needs_login, args.user, args.password)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
