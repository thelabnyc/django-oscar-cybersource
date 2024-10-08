from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("order", "0012_orderlinediscount"),
    ]

    operations = [
        migrations.AddField(
            model_name="line",
            name="allocation_cancelled",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="line",
            name="num_allocated",
            field=models.PositiveIntegerField(
                blank=True, null=True, verbose_name="Number allocated"
            ),
        ),
    ]
