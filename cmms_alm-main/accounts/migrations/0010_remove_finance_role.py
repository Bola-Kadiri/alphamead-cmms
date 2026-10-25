# Removes the FINANCE role. Every FINANCE user becomes HEAD OF FINANCE & TREASURY,
# which holds the same powers, so nobody loses access.

from django.db import migrations, models


def finance_to_head_of_finance(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    User.objects.filter(roles='FINANCE').update(roles='HEAD OF FINANCE & TREASURY')


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_five_stage_flow_roles'),
    ]

    operations = [
        # Not reversible by value: we cannot tell former FINANCE users apart afterwards.
        migrations.RunPython(finance_to_head_of_finance, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='user',
            name='roles',
            field=models.CharField(choices=[('SUPER ADMIN', 'Super Admin'), ('ADMIN', 'Admin'), ('REQUESTER', 'Requester (Site Manager)'), ('REVIEWER', 'Reviewer (Internal Control)'), ('APPROVER', 'Approver (Category Manager)'), ('PROCUREMENT AND STORE', 'Procurement and store'), ('CLIENT', 'Client (Client Contract Rep)'), ('CENTRAL OPERATION', 'Central Operation'), ('AP OFFICER', 'AP Officer'), ('HEAD OF FINANCE & TREASURY', 'Head of Finance & Treasury'), ('CONTRACTOR', 'Contractor (Vendor)')], default='Facility View', help_text='Type of user.', max_length=50),
        ),
    ]
