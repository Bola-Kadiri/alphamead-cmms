from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('facility', '0001_initial'),
        ('work', '0007_ppm_use_asset_categories'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='ppm',
            name='apartments',
        ),
        migrations.AddField(
            model_name='ppm',
            name='buildings',
            field=models.ManyToManyField(
                blank=True,
                help_text='Buildings associated with the maintenance.',
                related_name='ppms',
                to='facility.building',
            ),
        ),
    ]
