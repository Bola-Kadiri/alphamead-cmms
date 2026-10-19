from django.db import migrations, models


class Migration(migrations.Migration):
    """Vendor phone and bank details become optional. No existing data changes."""

    dependencies = [
        ('accounts', '0007_alter_user_roles'),
    ]

    operations = [
        migrations.AlterField(
            model_name='vendor',
            name='phone',
            field=models.CharField(blank=True, default='', help_text="Vendor's phone number.", max_length=15),
        ),
        migrations.AlterField(
            model_name='vendor',
            name='account_name',
            field=models.CharField(blank=True, default='', help_text='Bank account name.', max_length=255),
        ),
        migrations.AlterField(
            model_name='vendor',
            name='bank',
            field=models.CharField(blank=True, default='', help_text='Bank name.', max_length=255),
        ),
        migrations.AlterField(
            model_name='vendor',
            name='account_number',
            field=models.CharField(blank=True, help_text='Bank account number.', max_length=20, null=True, unique=True),
        ),
    ]
