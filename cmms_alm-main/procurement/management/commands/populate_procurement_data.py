"""
Management command to populate procurement models with sample data
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta

from accounts.models import Vendor, Department
from facility.models import Facility
from procurement.models import (
    RequestForQuotation,
    PurchaseOrder,
    PurchaseOrderRequisition,
    GoodsReceivedNote,
    VendorContract
)
from procurement.enum import RFQType, VendorContractType, PurchaseOrderStatus

User = get_user_model()


class Command(BaseCommand):
    help = 'Populate procurement models with sample data'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting to populate procurement data...'))

        # Get or create a user
        user, created = User.objects.get_or_create(
            email='admin@example.com',
            defaults={
                'first_name': 'Admin',
                'last_name': 'User',
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
            }
        )
        if created:
            user.set_password('admin123')
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Created user: {user.email}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Using existing user: {user.email}'))

        # Create Vendors
        vendors = []
        vendor_data = [
            {'name': 'ABC Supplies Ltd', 'type': 'Company', 'phone': '+1234567890', 'account_name': 'ABC Supplies', 'bank': 'First Bank', 'account_number': '1234567890', 'currency': 'NGN'},
            {'name': 'XYZ Services Inc', 'type': 'Company', 'phone': '+1234567891', 'account_name': 'XYZ Services', 'bank': 'GT Bank', 'account_number': '2345678901', 'currency': 'NGN'},
            {'name': 'Global Equipment Co', 'type': 'Company', 'phone': '+1234567892', 'account_name': 'Global Equipment', 'bank': 'Access Bank', 'account_number': '3456789012', 'currency': 'NGN'},
        ]
        
        for v_data in vendor_data:
            vendor, created = Vendor.objects.get_or_create(
                name=v_data['name'],
                defaults={**v_data, 'owner': user}
            )
            vendors.append(vendor)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created vendor: {vendor.name}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Using existing vendor: {vendor.name}'))

        # Create Department
        department, created = Department.objects.get_or_create(
            name='Procurement Department',
            defaults={'owner': user}
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created department: {department.name}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Using existing department: {department.name}'))

        # Create Facility
        facility, created = Facility.objects.get_or_create(
            name='Main Office Facility',
            defaults={'owner': user}
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created facility: {facility.name}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Using existing facility: {facility.name}'))

        # Create RequestForQuotation
        rfqs = []
        rfq_data = [
            {
                'title': 'Office Supplies RFQ',
                'type': RFQType.IFM_SERVICES,
                'currency': 'NGN',
                'terms': 'Payment within 30 days',
                'requester': user,
                'facility': facility,
            },
            {
                'title': 'IT Equipment Supply',
                'type': RFQType.SUPPLY,
                'currency': 'NGN',
                'terms': 'Delivery within 2 weeks',
                'requester': user,
                'facility': facility,
            },
            {
                'title': 'Cleaning Services',
                'type': RFQType.GENERAL_SERVICES,
                'currency': 'NGN',
                'terms': 'Monthly contract',
                'requester': user,
                'facility': facility,
            },
        ]

        for rfq_data_item in rfq_data:
            rfq, created = RequestForQuotation.objects.get_or_create(
                title=rfq_data_item['title'],
                defaults={**rfq_data_item, 'owner': user}
            )
            if created:
                rfq.vendors.set(vendors[:2])  # Add first 2 vendors
                self.stdout.write(self.style.SUCCESS(f'Created RFQ: {rfq.title}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Using existing RFQ: {rfq.title}'))
            rfqs.append(rfq)

        # Create PurchaseOrder
        purchase_orders = []
        po_data = [
            {
                'type': 'Office Supplies',
                'facility': facility,
                'department': department,
                'requested_by': user,
                'requested_date': date.today(),
                'vendor': vendors[0],
                'status': PurchaseOrderStatus.DRAFT,
            },
            {
                'type': 'IT Equipment',
                'facility': facility,
                'department': department,
                'requested_by': user,
                'requested_date': date.today() - timedelta(days=5),
                'vendor': vendors[1],
                'status': PurchaseOrderStatus.PENDING,
            },
        ]

        for po_data_item in po_data:
            po, created = PurchaseOrder.objects.get_or_create(
                type=po_data_item['type'],
                facility=po_data_item['facility'],
                requested_date=po_data_item['requested_date'],
                defaults={**po_data_item, 'owner': user}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created Purchase Order: {po.type}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Using existing Purchase Order: {po.type}'))
            purchase_orders.append(po)

        # Create PurchaseOrderRequisition
        po_requisitions = []
        por_data = [
            {
                'title': 'Office Furniture Requisition',
                'vendor': vendors[0],
                'description': 'Request for office chairs and desks',
                'amount': 500000.00,
                'expected_delivery_date': date.today() + timedelta(days=30),
                'sage_reference_number': 'SAGE-001',
            },
            {
                'title': 'IT Equipment Requisition',
                'vendor': vendors[1],
                'description': 'Request for laptops and monitors',
                'amount': 2500000.00,
                'expected_delivery_date': date.today() + timedelta(days=14),
                'sage_reference_number': 'SAGE-002',
            },
        ]

        for por_data_item in por_data:
            por, created = PurchaseOrderRequisition.objects.get_or_create(
                title=por_data_item['title'],
                defaults={**por_data_item, 'owner': user}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created PO Requisition: {por.title} (Invoice: {por.invoice_number})'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Using existing PO Requisition: {por.title}'))
            po_requisitions.append(por)

        # Create GoodsReceivedNote
        grns = []
        grn_data = [
            {
                'date_of_receipt': date.today() - timedelta(days=2),
                'purchase_order': purchase_orders[0],
                'vendor': vendors[0],
                'delivery_note_number': 'DN-001',
                'invoice_number': 'INV-001',
                'facility': facility,
                'received_by': user,
            },
            {
                'date_of_receipt': date.today() - timedelta(days=1),
                'purchase_order': purchase_orders[1],
                'vendor': vendors[1],
                'delivery_note_number': 'DN-002',
                'invoice_number': 'INV-002',
                'facility': facility,
                'received_by': user,
            },
        ]

        for grn_data_item in grn_data:
            grn, created = GoodsReceivedNote.objects.get_or_create(
                purchase_order=grn_data_item['purchase_order'],
                date_of_receipt=grn_data_item['date_of_receipt'],
                defaults={**grn_data_item, 'owner': user}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created GRN: {grn.grn_number}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Using existing GRN: {grn.grn_number}'))
            grns.append(grn)

        # Create VendorContract
        contracts = []
        contract_data = [
            {
                'contract_title': 'Annual Office Supplies Contract',
                'vendor': vendors[0],
                'contract_type': VendorContractType.SERVICE,
                'start_date': date.today(),
                'end_date': date.today() + timedelta(days=365),
                'proposed_value': 5000000.00,
                'reviewer': user,
            },
            {
                'contract_title': 'IT Equipment Purchase Agreement',
                'vendor': vendors[1],
                'contract_type': VendorContractType.PURCHASE,
                'start_date': date.today(),
                'end_date': date.today() + timedelta(days=180),
                'proposed_value': 10000000.00,
                'reviewer': user,
            },
        ]

        for contract_data_item in contract_data:
            contract, created = VendorContract.objects.get_or_create(
                contract_title=contract_data_item['contract_title'],
                defaults={**contract_data_item, 'owner': user}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created Vendor Contract: {contract.contract_title}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Using existing Vendor Contract: {contract.contract_title}'))
            contracts.append(contract)

        self.stdout.write(self.style.SUCCESS('\n=== Summary ==='))
        self.stdout.write(self.style.SUCCESS(f'Users: {User.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'Vendors: {Vendor.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'Facilities: {Facility.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'Departments: {Department.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'RFQs: {RequestForQuotation.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'Purchase Orders: {PurchaseOrder.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'PO Requisitions: {PurchaseOrderRequisition.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'GRNs: {GoodsReceivedNote.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'Vendor Contracts: {VendorContract.objects.count()}'))
        self.stdout.write(self.style.SUCCESS('\nProcurement data populated successfully!'))

