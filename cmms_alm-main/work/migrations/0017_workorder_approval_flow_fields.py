from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('work', '0016_workorder_is_reviewed'),
    ]

    operations = [
        migrations.AddField(
            model_name='workorder',
            name='reviewer_reason',
            field=models.TextField(blank=True, null=True, help_text='Reason provided when a reviewer rejects the work order.'),
        ),
        migrations.AddField(
            model_name='workorder',
            name='approver_reason',
            field=models.TextField(blank=True, null=True, help_text='Reason provided when an approver rejects the work order.'),
        ),
        migrations.AddField(
            model_name='workorder',
            name='digital_signature',
            field=models.CharField(max_length=255, blank=True, null=True, help_text="Approver's digital signature (full name) on final approval."),
        ),
        migrations.AlterField(
            model_name='workorder',
            name='approval_status',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('Pending', 'Pending'),
                    ('Reviewed', 'Reviewed'),
                    ('Approved', 'Approved'),
                    ('Reviewer Rejected', 'Reviewer Rejected'),
                    ('Approver Rejected', 'Approver Rejected'),
                    ('Rejected', 'Rejected'),
                ],
                default='Pending',
                help_text='Approval status of the work order.',
            ),
        ),
    ]
