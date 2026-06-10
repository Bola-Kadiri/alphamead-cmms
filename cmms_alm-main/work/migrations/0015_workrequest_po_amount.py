from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('work', '0014_workrequest_po_document'),
    ]

    operations = [
        migrations.AddField(
            model_name='workrequest',
            name='po_amount',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=18,
                null=True,
                help_text='PO amount entered by Procurement & Store on approval.',
            ),
        ),
    ]
