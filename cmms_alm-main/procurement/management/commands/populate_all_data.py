"""
Management command to populate all modules with reference data
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta

# Accounts models
from accounts.models import (
    User, Vendor, Client, Department, Category, Subcategory,
    BankAccount, Personnel, UnitOfMeasurement, Contact
)

# Facility models
from facility.models import (
    Region, Cluster, Facility, Zone, Building, Subsystem,
    ApartmentType, Apartment, Landlord
)

# Procurement models
from procurement.models import (
    RequestForQuotation,
    PurchaseOrder,
    PurchaseOrderRequisition,
    GoodsReceivedNote,
    VendorContract
)
from procurement.enum import RFQType, VendorContractType, PurchaseOrderStatus

UserModel = get_user_model()


class Command(BaseCommand):
    help = 'Populate all modules with reference data'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting to populate all modules with data...'))

        # ========== ACCOUNTS MODULE ==========
        self.stdout.write(self.style.SUCCESS('\n=== Populating Accounts Module ==='))

        # Create Users
        users = []
        user_data = [
            {'email': 'admin@example.com', 'first_name': 'Admin', 'last_name': 'User', 'roles': 'Super Admin', 'is_staff': True, 'is_superuser': True},
            {'email': 'facility.admin@example.com', 'first_name': 'Facility', 'last_name': 'Admin', 'roles': 'Facility Admin'},
            {'email': 'procurement@example.com', 'first_name': 'Procurement', 'last_name': 'Manager', 'roles': 'Facility Procurement'},
            {'email': 'manager@example.com', 'first_name': 'Facility', 'last_name': 'Manager', 'roles': 'Facility Manager'},
        ]

        for u_data in user_data:
            user, created = UserModel.objects.get_or_create(
                email=u_data['email'],
                defaults={**{k: v for k, v in u_data.items() if k != 'is_staff' and k != 'is_superuser'}, 'is_active': True}
            )
            if created:
                if u_data.get('is_staff'):
                    user.is_staff = True
                if u_data.get('is_superuser'):
                    user.is_superuser = True
                user.set_password('admin123')
                user.save()
                self.stdout.write(self.style.SUCCESS(f'  Created user: {user.email}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'  Using existing user: {user.email}'))
            users.append(user)

        admin_user = users[0]

        # Create Departments
        departments = []
        dept_data = [
            {'code': 'PROC', 'name': 'Procurement Department', 'email': 'procurement@example.com', 'phone': '+1234567001'},
            {'code': 'IT', 'name': 'IT Department', 'email': 'it@example.com', 'phone': '+1234567002'},
            {'code': 'FIN', 'name': 'Finance Department', 'email': 'finance@example.com', 'phone': '+1234567003'},
            {'code': 'OPS', 'name': 'Operations Department', 'email': 'operations@example.com', 'phone': '+1234567004'},
            {'code': 'HR', 'name': 'HR Department', 'email': 'hr@example.com', 'phone': '+1234567005'},
        ]

        for d_data in dept_data:
            dept, created = Department.objects.get_or_create(
                code=d_data['code'],
                defaults={**{k: v for k, v in d_data.items()}, 'owner': admin_user, 'status': 'Active'}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  Created department: {dept.name}'))
            departments.append(dept)

        # Create Categories
        categories = []
        category_data = [
            {'code': 'OFF-SUP', 'title': 'Office Supplies'},
            {'code': 'IT-EQP', 'title': 'IT Equipment'},
            {'code': 'FURN', 'title': 'Furniture'},
            {'code': 'CLEAN', 'title': 'Cleaning Supplies'},
            {'code': 'MAINT', 'title': 'Maintenance Services'},
        ]

        for c_data in category_data:
            cat, created = Category.objects.get_or_create(
                code=c_data['code'],
                defaults={**{k: v for k, v in c_data.items()}, 'owner': admin_user, 'status': 'Active'}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  Created category: {cat.code}'))
            categories.append(cat)

        # Create Subcategories
        subcategories = []
        subcat_data = [
            {'title': 'Laptops', 'category': categories[1]},
            {'title': 'Desktops', 'category': categories[1]},
            {'title': 'Office Chairs', 'category': categories[2]},
            {'title': 'Desks', 'category': categories[2]},
        ]

        for sc_data in subcat_data:
            subcat, created = Subcategory.objects.get_or_create(
                title=sc_data['title'],
                category=sc_data['category'],
                defaults={**{k: v for k, v in sc_data.items()}, 'owner': admin_user, 'status': 'Active'}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  Created subcategory: {subcat.title}'))
            subcategories.append(subcat)

        # Create Vendors
        vendors = []
        vendor_data = [
            {'name': 'ABC Supplies Ltd', 'type': 'Company', 'phone': '+1234567890', 'email': 'info@abcsupplies.com', 'account_name': 'ABC Supplies', 'bank': 'First Bank', 'account_number': '1234567890', 'currency': 'NGN'},
            {'name': 'XYZ Services Inc', 'type': 'Company', 'phone': '+1234567891', 'email': 'contact@xyzservices.com', 'account_name': 'XYZ Services', 'bank': 'GT Bank', 'account_number': '2345678901', 'currency': 'NGN'},
            {'name': 'Global Equipment Co', 'type': 'Company', 'phone': '+1234567892', 'email': 'sales@globalequip.com', 'account_name': 'Global Equipment', 'bank': 'Access Bank', 'account_number': '3456789012', 'currency': 'NGN'},
            {'name': 'Tech Solutions Ltd', 'type': 'Company', 'phone': '+1234567893', 'email': 'info@techsolutions.com', 'account_name': 'Tech Solutions', 'bank': 'Zenith Bank', 'account_number': '4567890123', 'currency': 'NGN'},
        ]

        for v_data in vendor_data:
            vendor, created = Vendor.objects.get_or_create(
                name=v_data['name'],
                defaults={**{k: v for k, v in v_data.items()}, 'owner': admin_user, 'status': 'Active'}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  Created vendor: {vendor.name}'))
            vendors.append(vendor)

        # Create Clients
        clients = []
        client_data = [
            {'code': 'ACME', 'name': 'Acme Corporation', 'type': 'Company', 'phone': '+1234567900', 'email': 'contact@acme.com'},
            {'code': 'TECH', 'name': 'Tech Industries', 'type': 'Company', 'phone': '+1234567901', 'email': 'info@techindustries.com'},
        ]

        for cl_data in client_data:
            client, created = Client.objects.get_or_create(
                code=cl_data['code'],
                defaults={**{k: v for k, v in cl_data.items()}, 'owner': admin_user, 'status': 'Active'}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  Created client: {client.name}'))
            clients.append(client)

        # Create Bank Accounts
        bank_accounts = []
        bank_data = [
            {'bank': 'First Bank', 'account_name': 'Main Operating Account', 'account_number': '9876543210', 'currency': 'NGN'},
            {'bank': 'GT Bank', 'account_name': 'Savings Account', 'account_number': '8765432109', 'currency': 'NGN'},
        ]

        for b_data in bank_data:
            bank, created = BankAccount.objects.get_or_create(
                account_number=b_data['account_number'],
                defaults={**b_data, 'owner': admin_user, 'status': 'Active'}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  Created bank account: {bank.account_name}'))
            bank_accounts.append(bank)

        # Create Unit of Measurement
        units = []
        unit_data = [
            {'code': 'PCS', 'symbol': 'pcs', 'description': 'Piece', 'type': 'Piece'},
            {'code': 'KG', 'symbol': 'kg', 'description': 'Kilogram', 'type': 'Weight'},
            {'code': 'L', 'symbol': 'L', 'description': 'Liter', 'type': 'Volume'},
            {'code': 'M', 'symbol': 'm', 'description': 'Meter', 'type': 'Area'},
            {'code': 'BOX', 'symbol': 'box', 'description': 'Box', 'type': 'Packing'},
        ]

        for u_data in unit_data:
            unit, created = UnitOfMeasurement.objects.get_or_create(
                code=u_data['code'],
                defaults={**{k: v for k, v in u_data.items()}, 'owner': admin_user, 'status': 'Active'}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  Created unit: {unit.code}'))
            units.append(unit)

        # ========== FACILITY MODULE ==========
        self.stdout.write(self.style.SUCCESS('\n=== Populating Facility Module ==='))

        # Create Regions
        regions = []
        region_data = [
            {'name': 'Lagos Region', 'country': 'Nigeria'},
            {'name': 'Abuja Region', 'country': 'Nigeria'},
            {'name': 'Port Harcourt Region', 'country': 'Nigeria'},
        ]

        for r_data in region_data:
            region, created = Region.objects.get_or_create(
                name=r_data['name'],
                defaults={**{k: v for k, v in r_data.items()}, 'owner': admin_user}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  Created region: {region.name}'))
            regions.append(region)

        # Create Clusters
        clusters = []
        cluster_data = [
            {'name': 'Lagos Main Cluster', 'region': regions[0]},
            {'name': 'Abuja Central Cluster', 'region': regions[1]},
            {'name': 'Port Harcourt Cluster', 'region': regions[2]},
        ]

        for cl_data in cluster_data:
            cluster, created = Cluster.objects.get_or_create(
                name=cl_data['name'],
                defaults={**{k: v for k, v in cl_data.items()}, 'owner': admin_user}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  Created cluster: {cluster.name}'))
            clusters.append(cluster)

        # Create Facilities
        facilities = []
        facility_data = [
            {'name': 'Main Office Facility', 'cluster': clusters[0], 'type': 'Office', 'address_gps': '6.5244, 3.3792'},
            {'name': 'Warehouse Facility', 'cluster': clusters[0], 'type': 'Warehouse', 'address_gps': '6.5244, 3.3792'},
            {'name': 'Abuja Branch Office', 'cluster': clusters[1], 'type': 'Office', 'address_gps': '9.0765, 7.3986'},
        ]

        for f_data in facility_data:
            facility, created = Facility.objects.get_or_create(
                name=f_data['name'],
                defaults={**{k: v for k, v in f_data.items()}, 'owner': admin_user, 'manager': users[1]}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  Created facility: {facility.name}'))
            facilities.append(facility)

        # Create Zones
        zones = []
        zone_data = [
            {'code': 'ZONE-A', 'name': 'Zone A', 'facility': facilities[0]},
            {'code': 'ZONE-B', 'name': 'Zone B', 'facility': facilities[0]},
            {'code': 'ZONE-C', 'name': 'Zone C', 'facility': facilities[1]},
        ]

        for z_data in zone_data:
            zone, created = Zone.objects.get_or_create(
                code=z_data['code'],
                defaults={**{k: v for k, v in z_data.items()}, 'owner': admin_user}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  Created zone: {zone.name}'))
            zones.append(zone)

        # Create Buildings
        buildings = []
        building_data = [
            {'code': 'BLD-A', 'name': 'Building A', 'facility': facilities[0], 'zone': zones[0]},
            {'code': 'BLD-B', 'name': 'Building B', 'facility': facilities[0], 'zone': zones[1]},
            {'code': 'BLD-WH', 'name': 'Warehouse Building', 'facility': facilities[1], 'zone': zones[2]},
        ]

        for b_data in building_data:
            building, created = Building.objects.get_or_create(
                code=b_data['code'],
                defaults={**{k: v for k, v in b_data.items()}, 'owner': admin_user, 'status': 'Active'}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  Created building: {building.name}'))
            buildings.append(building)

        # Create Subsystems
        subsystems = []
        subsystem_data = [
            {'name': 'HVAC System', 'facility': facilities[0], 'building': buildings[0]},
            {'name': 'Electrical System', 'facility': facilities[0], 'building': buildings[0]},
            {'name': 'Plumbing System', 'facility': facilities[0], 'building': buildings[1]},
        ]

        for s_data in subsystem_data:
            subsystem, created = Subsystem.objects.get_or_create(
                name=s_data['name'],
                building=s_data['building'],
                defaults={**{k: v for k, v in s_data.items()}, 'owner': admin_user}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  Created subsystem: {subsystem.name}'))
            subsystems.append(subsystem)

        # Create Apartment Types
        apartment_types = []
        apt_type_data = [
            {'name': 'Studio'},
            {'name': '1-Bedroom'},
            {'name': '2-Bedroom'},
            {'name': '3-Bedroom'},
        ]

        for at_data in apt_type_data:
            apt_type, created = ApartmentType.objects.get_or_create(
                name=at_data['name'],
                defaults={'owner': admin_user, 'status': 'Active'}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  Created apartment type: {apt_type.name}'))
            apartment_types.append(apt_type)

        # Create Landlords
        landlords = []
        landlord_data = [
            {'name': 'John Doe Properties', 'phone': '+1234568000', 'email': 'john@properties.com'},
            {'name': 'Jane Smith Realty', 'phone': '+1234568001', 'email': 'jane@realty.com'},
        ]

        for ll_data in landlord_data:
            landlord, created = Landlord.objects.get_or_create(
                name=ll_data['name'],
                defaults={**ll_data, 'owner': admin_user, 'status': 'Active'}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  Created landlord: {landlord.name}'))
            landlords.append(landlord)

        # Create Apartments
        apartments = []
        apartment_data = [
            {'no': 'APT-101', 'type': 'Studio', 'apartment_type': apartment_types[0], 'building': buildings[0], 'landlord': landlords[0], 'ownership_type': 'Freehold'},
            {'no': 'APT-102', 'type': '1-Bedroom', 'apartment_type': apartment_types[1], 'building': buildings[0], 'landlord': landlords[0], 'ownership_type': 'Leasehold'},
            {'no': 'APT-201', 'type': '2-Bedroom', 'apartment_type': apartment_types[2], 'building': buildings[1], 'landlord': landlords[1], 'ownership_type': 'Freehold'},
        ]

        for a_data in apartment_data:
            apartment, created = Apartment.objects.get_or_create(
                no=a_data['no'],
                defaults={**{k: v for k, v in a_data.items() if k != 'apartment_type'}, 'owner': admin_user, 'status': 'Active'}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  Created apartment: {apartment.no}'))
            apartments.append(apartment)

        # ========== PROCUREMENT MODULE ==========
        self.stdout.write(self.style.SUCCESS('\n=== Populating Procurement Module ==='))

        # Create RequestForQuotation
        rfqs = []
        rfq_data = [
            {
                'title': 'Office Supplies RFQ',
                'type': RFQType.IFM_SERVICES,
                'currency': 'NGN',
                'terms': 'Payment within 30 days',
                'requester': users[2],
                'facility': facilities[0],
            },
            {
                'title': 'IT Equipment Supply',
                'type': RFQType.SUPPLY,
                'currency': 'NGN',
                'terms': 'Delivery within 2 weeks',
                'requester': users[2],
                'facility': facilities[0],
            },
            {
                'title': 'Cleaning Services',
                'type': RFQType.GENERAL_SERVICES,
                'currency': 'NGN',
                'terms': 'Monthly contract',
                'requester': users[2],
                'facility': facilities[0],
            },
        ]

        for rfq_data_item in rfq_data:
            rfq, created = RequestForQuotation.objects.get_or_create(
                title=rfq_data_item['title'],
                defaults={**rfq_data_item, 'owner': admin_user}
            )
            if created:
                rfq.vendors.set(vendors[:2])
                self.stdout.write(self.style.SUCCESS(f'  Created RFQ: {rfq.title}'))
            rfqs.append(rfq)

        # Create PurchaseOrder
        purchase_orders = []
        po_data = [
            {
                'type': 'Office Supplies',
                'facility': facilities[0],
                'department': departments[0],
                'requested_by': users[2],
                'requested_date': date.today(),
                'vendor': vendors[0],
                'status': PurchaseOrderStatus.DRAFT,
            },
            {
                'type': 'IT Equipment',
                'facility': facilities[0],
                'department': departments[1],
                'requested_by': users[2],
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
                defaults={**po_data_item, 'owner': admin_user}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  Created Purchase Order: {po.type}'))
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
                defaults={**por_data_item, 'owner': admin_user}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  Created PO Requisition: {por.title} (Invoice: {por.invoice_number})'))
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
                'facility': facilities[0],
                'received_by': users[2],
            },
            {
                'date_of_receipt': date.today() - timedelta(days=1),
                'purchase_order': purchase_orders[1],
                'vendor': vendors[1],
                'delivery_note_number': 'DN-002',
                'invoice_number': 'INV-002',
                'facility': facilities[0],
                'received_by': users[2],
            },
        ]

        for grn_data_item in grn_data:
            grn, created = GoodsReceivedNote.objects.get_or_create(
                purchase_order=grn_data_item['purchase_order'],
                date_of_receipt=grn_data_item['date_of_receipt'],
                defaults={**grn_data_item, 'owner': admin_user}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  Created GRN: {grn.grn_number}'))
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
                'reviewer': users[1],
            },
            {
                'contract_title': 'IT Equipment Purchase Agreement',
                'vendor': vendors[1],
                'contract_type': VendorContractType.PURCHASE,
                'start_date': date.today(),
                'end_date': date.today() + timedelta(days=180),
                'proposed_value': 10000000.00,
                'reviewer': users[1],
            },
        ]

        for contract_data_item in contract_data:
            contract, created = VendorContract.objects.get_or_create(
                contract_title=contract_data_item['contract_title'],
                defaults={**contract_data_item, 'owner': admin_user}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  Created Vendor Contract: {contract.contract_title}'))
            contracts.append(contract)

        # ========== SUMMARY ==========
        self.stdout.write(self.style.SUCCESS('\n=== Summary ==='))
        self.stdout.write(self.style.SUCCESS(f'Users: {UserModel.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'Departments: {Department.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'Categories: {Category.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'Subcategories: {Subcategory.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'Vendors: {Vendor.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'Clients: {Client.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'Bank Accounts: {BankAccount.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'Units of Measurement: {UnitOfMeasurement.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'Regions: {Region.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'Clusters: {Cluster.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'Facilities: {Facility.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'Zones: {Zone.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'Buildings: {Building.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'Subsystems: {Subsystem.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'Apartment Types: {ApartmentType.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'Landlords: {Landlord.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'Apartments: {Apartment.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'RFQs: {RequestForQuotation.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'Purchase Orders: {PurchaseOrder.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'PO Requisitions: {PurchaseOrderRequisition.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'GRNs: {GoodsReceivedNote.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'Vendor Contracts: {VendorContract.objects.count()}'))
        self.stdout.write(self.style.SUCCESS('\nAll modules populated successfully!'))
        self.stdout.write(self.style.SUCCESS('\nDefault login credentials:'))
        self.stdout.write(self.style.SUCCESS('  Email: admin@example.com'))
        self.stdout.write(self.style.SUCCESS('  Password: admin123'))

