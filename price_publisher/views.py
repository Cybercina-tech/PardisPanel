from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from category.models import Category
from price_publisher.forms import PriceTemplateForm
from price_publisher.models import PriceTemplate
from special_price.models import SpecialPriceType


@login_required
def template_dashboard(request):
    templates = (
        PriceTemplate.objects.select_related("category", "special_price_type")
        .order_by("template_type", "name")
        .all()
    )

    categories_without_template = (
        Category.objects.order_by("name")
        .filter(price_template__isnull=True)
    )

    special_without_template = (
        SpecialPriceType.objects.order_by("name")
        .filter(price_template__isnull=True)
    )

    asset_root = Path(settings.BASE_DIR) / "assets"

    def _collect_assets(subdir: str, patterns: tuple[str, ...] = ("*.png", "*.jpg", "*.jpeg", "*.webp")):
        folder = asset_root / subdir
        if not folder.exists():
            return []
        files: list[str] = []
        for pattern in patterns:
            for file in sorted(folder.glob(pattern)):
                files.append(f"{subdir}/{file.name}")
        return files

    def _collect_root(patterns: tuple[str, ...] = ("*.png", "*.jpg", "*.jpeg", "*.webp")):
        files: list[str] = []
        if not asset_root.exists():
            return files
        for pattern in patterns:
            for file in sorted(asset_root.glob(pattern)):
                files.append(file.name)
        return files

    asset_catalog = {
        "price_theme": _collect_assets("price_theme"),
        "offer": _collect_assets("offer"),
        "news": _collect_assets("news"),
        "general": _collect_root(),
        "fonts": sorted(
            (Path("fonts") / font.name).as_posix()
            for font in (asset_root / "fonts").glob("*")
            if font.is_file()
        )
        if (asset_root / "fonts").exists()
        else [],
    }

    context = {
        "templates": templates,
        "categories_without_template": categories_without_template,
        "special_without_template": special_without_template,
        "asset_catalog": asset_catalog,
    }

    return render(request, "price_publisher/template_dashboard.html", context)


@login_required
def template_create(request):
    if request.method == "POST":
        form = PriceTemplateForm(request.POST, request.FILES)
        if form.is_valid():
            template = form.save()
            messages.success(
                request,
                f"Template '{template.name}' created successfully.",
            )
            return redirect("price_publisher:template_dashboard")
    else:
        form = PriceTemplateForm()

    return render(
        request,
        "price_publisher/template_form.html",
        {"form": form, "is_edit": False},
    )


@login_required
def template_update(request, pk: int):
    template = get_object_or_404(PriceTemplate, pk=pk)

    if request.method == "POST":
        form = PriceTemplateForm(request.POST, request.FILES, instance=template)
        if form.is_valid():
            template = form.save()
            messages.success(
                request,
                f"Template '{template.name}' updated successfully.",
            )
            return redirect("price_publisher:template_dashboard")
    else:
        form = PriceTemplateForm(instance=template)

    return render(
        request,
        "price_publisher/template_form.html",
        {"form": form, "is_edit": True, "template_obj": template},
    )


@login_required
def template_delete(request, pk: int):
    template = get_object_or_404(PriceTemplate, pk=pk)

    if request.method == "POST":
        name = template.name
        template.delete()
        messages.success(request, f"Template '{name}' deleted successfully.")
        return redirect("price_publisher:template_dashboard")

    return render(
        request,
        "price_publisher/template_confirm_delete.html",
        {"template_obj": template},
    )


@login_required
def template_editor_redirect(request, pk: int):
    template = get_object_or_404(PriceTemplate, pk=pk)
    editor_url = reverse("template_editor_frontend:editor", args=[template.pk])
    return redirect(editor_url)


@login_required
def template_editor_index(request):
    first_template = (
        PriceTemplate.objects.order_by("template_type", "name").first()
    )
    if first_template:
        return redirect("price_publisher:template_editor", pk=first_template.pk)
    messages.info(
        request,
        "Create a template before opening the visual editor.",
    )
    return redirect("price_publisher:template_create")


