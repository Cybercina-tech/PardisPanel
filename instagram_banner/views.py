import base64
import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.db.models import Prefetch
from django.utils import timezone

from category.models import Category, PriceType
from change_price.models import PriceHistory
from core.sorting import sort_categories, sort_price_types_by_category
from .services import generate_story_banner, generate_post_banner

logger = logging.getLogger(__name__)


def _get_latest_price_items(category):
    """Return list of (price_type, latest_price_history) for a category."""
    price_types = PriceType.objects.filter(category=category).select_related(
        "source_currency", "target_currency"
    ).prefetch_related("price_histories")

    price_types = sort_price_types_by_category(list(price_types), category.name)

    items = []
    for pt in price_types:
        latest = pt.price_histories.first()
        if latest:
            items.append((pt, latest))
    return items


@login_required
def generator_page(request):
    """Landing page for the Instagram banner generator."""
    categories = Category.objects.prefetch_related(
        Prefetch(
            "price_types",
            queryset=PriceType.objects.prefetch_related("price_histories").select_related(
                "source_currency", "target_currency"
            ),
        )
    ).all()

    sorted_cats = sort_categories(categories)

    context = {
        "categories": sorted_cats,
    }
    return render(request, "instagram_banner/generator.html", context)


def _render_banner(category_id: int, format_type: str):
    """Shared helper: render a banner and return the PNG bytes."""
    category = get_object_or_404(Category, id=category_id)
    price_items = _get_latest_price_items(category)

    if not price_items:
        return None, "No prices available for this category."

    try:
        if format_type == "story":
            buf = generate_story_banner(category, price_items)
        elif format_type == "post":
            buf = generate_post_banner(category, price_items)
        else:
            return None, f"Invalid format: {format_type}"
    except Exception as exc:
        logger.error("Banner generation failed: %s", exc, exc_info=True)
        return None, str(exc)

    buf.seek(0)
    return buf.read(), None


@login_required
def preview_image(request, category_id: int, format_type: str):
    """Return a base64-encoded preview as JSON for AJAX display."""
    data, err = _render_banner(category_id, format_type)
    if err:
        return JsonResponse({"error": err}, status=400)

    b64 = base64.b64encode(data).decode("ascii")
    return JsonResponse({"image": f"data:image/png;base64,{b64}"})


@login_required
def download_image(request, category_id: int, format_type: str):
    """Stream the rendered PNG as a downloadable file."""
    data, err = _render_banner(category_id, format_type)
    if err:
        return HttpResponse(err, status=400)

    category = get_object_or_404(Category, id=category_id)
    slug = category.slug or "banner"
    filename = f"pardis_{slug}_{format_type}.png"

    response = HttpResponse(data, content_type="image/png")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
