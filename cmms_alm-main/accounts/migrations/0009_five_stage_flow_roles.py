# Five-stage Work Request flow: new roles (CENTRAL OPERATION, AP OFFICER,
# HEAD OF FINANCE & TREASURY, CONTRACTOR), clearer labels on existing roles,
# and the vendor link for CONTRACTOR logins. Also joins the two 0008 branches.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_client_show_utility_bills_alter_user_roles'),
        ('accounts', '0008_vendor_optional_details'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='roles',
            field=models.CharField(choices=[('SUPER ADMIN', 'Super Admin'), ('ADMIN', 'Admin'), ('REQUESTER', 'Requester (Site Manager)'), ('REVIEWER', 'Reviewer (Internal Control)'), ('APPROVER', 'Approver (Category Manager)'), ('PROCUREMENT AND STORE', 'Procurement and store'), ('FINANCE', 'Finance'), ('CLIENT', 'Client (Client Contract Rep)'), ('CENTRAL OPERATION', 'Central Operation'), ('AP OFFICER', 'AP Officer'), ('HEAD OF FINANCE & TREASURY', 'Head of Finance & Treasury'), ('CONTRACTOR', 'Contractor (Vendor)')], default='Facility View', help_text='Type of user.', max_length=50),
        ),
        migrations.AddField(
            model_name='user',
            name='vendor',
            field=models.ForeignKey(blank=True, help_text='For CONTRACTOR users: the vendor this login belongs to.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='portal_users', to='accounts.vendor'),
        ),
    ]
