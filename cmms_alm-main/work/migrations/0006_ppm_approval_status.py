from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('work', '0005_work_order_nullable_fields_and_new'),
    ]

    operations = [
        migrations.AddField(
            model_name='ppm',
            name='approval_status',
            field=models.CharField(
                choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')],
                default='Pending',
                help_text='Approval status of the PPM schedule.',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='ppm',
            name='rejection_reason',
            field=models.TextField(
                blank=True,
                null=True,
                help_text='Reason for rejecting the PPM schedule.',
            ),
        ),
    ]
