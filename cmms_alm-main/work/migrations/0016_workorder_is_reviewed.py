from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('work', '0015_workrequest_po_amount'),
    ]

    operations = [
        migrations.AddField(
            model_name='workorder',
            name='is_reviewed',
            field=models.BooleanField(default=False, help_text='Indicates whether the work order has been reviewed.'),
        ),
    ]
