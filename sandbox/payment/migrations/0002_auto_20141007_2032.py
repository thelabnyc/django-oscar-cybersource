from django.db import migrations, models
import oscar.core.utils


class Migration(migrations.Migration):
    dependencies = [
        ("payment", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="source",
            name="currency",
            field=models.CharField(
                default=oscar.core.utils.get_default_currency,
                max_length=12,
                verbose_name="Currency",
            ),
        ),
    ]
