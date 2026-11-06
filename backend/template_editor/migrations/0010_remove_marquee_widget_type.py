# Remove marquee widget type from stored templates (convert to text).

import copy

from django.db import migrations


def forwards_remove_marquee(apps, schema_editor):
    Template = apps.get_model("template_editor", "Template")
    Widget = apps.get_model("template_editor", "Widget")

    for tpl in Template.objects.all().iterator():
        cj = tpl.config_json
        if not isinstance(cj, dict):
            continue
        widgets = cj.get("widgets")
        if not isinstance(widgets, list):
            continue
        changed = False
        new_cj = copy.deepcopy(cj)
        for w in new_cj["widgets"]:
            if isinstance(w, dict) and str(w.get("type") or "").strip() == "marquee":
                w["type"] = "text"
                changed = True
        if changed:
            tpl.config_json = new_cj
            tpl.save(update_fields=["config_json"])

    Widget.objects.filter(type="marquee").update(type="text")


def backwards_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("template_editor", "0009_template_contract_cutover"),
    ]

    operations = [
        migrations.RunPython(forwards_remove_marquee, backwards_noop),
    ]
