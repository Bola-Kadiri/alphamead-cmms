from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('work', '0011_workrequest_workflow_update'),
    ]

    operations = [
        migrations.RunSQL(
            sql="CREATE SEQUENCE IF NOT EXISTS work_request_number_seq START 1;",
            reverse_sql="DROP SEQUENCE IF EXISTS work_request_number_seq;",
        ),
        migrations.AlterField(
            model_name='workrequest',
            name='work_request_number',
            field=models.CharField(
                blank=True,
                max_length=15,
                help_text='Unique work request number in REQ-YYYY-NNNNN format.',
            ),
        ),
    ]
