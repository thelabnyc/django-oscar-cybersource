from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("payment", "0008_auto_20221116_1712"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="transaction",
            name="only_captures_have_auths",
        ),
        migrations.RemoveField(
            model_name="transaction",
            name="authorization",
        ),
    ]
