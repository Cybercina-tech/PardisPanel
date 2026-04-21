from django.db import migrations


def update_category_labels_and_descriptions(apps, schema_editor):
    Category = apps.get_model("category", "Category")

    tether_category = (
        Category.objects.filter(name__iregex=r"(تتر|tether|usdt)")
        .order_by("id")
        .first()
    )
    if tether_category:
        tether_category.name = "سایر ارز ها"
        tether_category.description = "خرید فروش تتر | لیر | یورو | درهم"
        tether_category.save(update_fields=["name", "description"])

    pound_categories = Category.objects.filter(name__iregex=r"(پوند|pound|gbp)")
    for category in pound_categories:
        if category.description and "| لیر | درهم" in category.description:
            category.description = category.description.replace(" | لیر | درهم", "")
            category.save(update_fields=["description"])


class Migration(migrations.Migration):
    dependencies = [
        ("category", "0008_ensure_tether_euro_pricetype"),
    ]

    operations = [
        migrations.RunPython(
            update_category_labels_and_descriptions,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
