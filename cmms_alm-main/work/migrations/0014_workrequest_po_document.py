from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('work', '0013_alter_workorder_department_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='workrequest',
            name='po_document',
            field=models.FileField(
                blank=True,
                null=True,
                upload_to='work_requests/po_documents/',
                help_text='PO document uploaded by Procurement & Store.',
            ),
        ),
        migrations.AlterField(
            model_name='workrequest',
            name='po_number',
            field=models.CharField(
                blank=True,
                max_length=100,
                null=True,
                help_text='Purchase Order number entered by Procurement & Store.',
            ),
        ),
    ]
