from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('work', '0017_workorder_approval_flow_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='workorder',
            name='allow_resubmission',
            field=models.BooleanField(
                default=False,
                help_text='Admin-controlled flag. When True, allows a new work order to be raised from the same source PPM or work request after rejection.',
            ),
        ),
    ]
