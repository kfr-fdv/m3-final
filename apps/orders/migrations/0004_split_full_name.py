from django.db import migrations, models


def split_full_name(apps, schema_editor):
    """Existing orders keep "First Last" in full_name."""
    Order = apps.get_model("orders", "Order")
    for order in Order.objects.exclude(full_name=""):
        first, _, last = order.full_name.strip().partition(" ")
        order.first_name, order.last_name = first, last.strip()
        order.save(update_fields=["first_name", "last_name"])


def join_full_name(apps, schema_editor):
    Order = apps.get_model("orders", "Order")
    for order in Order.objects.all():
        order.full_name = f"{order.first_name} {order.last_name}".strip()
        order.save(update_fields=["full_name"])


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0003_checkout_contacts_and_delivery"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="last_name",
            field=models.CharField(blank=True, max_length=150, verbose_name="прізвище"),
        ),
        migrations.AddField(
            model_name="order",
            name="first_name",
            field=models.CharField(blank=True, max_length=150, verbose_name="ім'я"),
        ),
        migrations.AddField(
            model_name="order",
            name="middle_name",
            field=models.CharField(blank=True, max_length=150, verbose_name="по батькові"),
        ),
        migrations.RunPython(split_full_name, join_full_name),
        migrations.RemoveField(model_name="order", name="full_name"),
    ]
