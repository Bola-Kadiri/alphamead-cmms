from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('work', '0003_workrequest_approver_workrequest_reviewers'),
    ]

    operations = [
        migrations.AddField(
            model_name='workrequest',
            name='reviewer_approval_status',
            field=models.CharField(
                choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')],
                default='Pending',
                help_text="Reviewer's secondary approval status (set after approver has approved).",
                max_length=10,
            ),
        ),
    ]
