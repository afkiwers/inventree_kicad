from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("inventree_kicad", "0008_alter_selectedcategory_footprint_parameter_template"),
    ]

    operations = [
        migrations.DeleteModel(
            name="ProgressIndicator",
        ),
    ]
