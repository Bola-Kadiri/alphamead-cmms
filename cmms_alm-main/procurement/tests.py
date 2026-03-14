from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
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


class ProcurementAPITestCase(TestCase):
    """Base test case for procurement API tests"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create test user
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.user.roles = 'Facility Admin'
        self.user.is_active = True
        self.user.save()
        self.client.force_authenticate(user=self.user)
        
        # Create test vendor
        self.vendor = Vendor.objects.create(
            name='Test Vendor',
            type='Company',
            phone='1234567890',
            account_name='Test Account',
            bank='Test Bank',
            account_number='1234567890',
            currency='NGN',
            owner=self.user
        )
        
        # Create test facility
        self.facility = Facility.objects.create(
            name='Test Facility',
            owner=self.user
        )
        
        # Create test department
        self.department = Department.objects.create(
            name='Test Department',
            owner=self.user
        )
        
        # Create test purchase order
        self.purchase_order = PurchaseOrder.objects.create(
            type='Test PO',
            facility=self.facility,
            department=self.department,
            requested_by=self.user,
            requested_date=date.today(),
            vendor=self.vendor,
            status=PurchaseOrderStatus.DRAFT,
            owner=self.user
        )


class RequestForQuotationAPITest(ProcurementAPITestCase):
    """Test Request for Quotation API endpoints"""
    
    def test_create_rfq(self):
        """Test creating a new RFQ"""
        url = '/procurement/api/request-quotation/'
        data = {
            'title': 'Test RFQ',
            'type': RFQType.IFM_SERVICES,
            'currency': 'NGN',
            'terms': 'Test terms',
            'requester': self.user.id,
            'facility': self.facility.id,
            'vendors': [self.vendor.id]
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['message'], 'RFQ created successfully')
        self.assertIn('data', response.data)
        self.assertEqual(response.data['data']['title'], 'Test RFQ')
    
    def test_list_rfqs(self):
        """Test listing RFQs"""
        # Create test RFQ
        RequestForQuotation.objects.create(
            title='Test RFQ 1',
            type=RFQType.IFM_SERVICES,
            currency='NGN',
            owner=self.user
        )
        RequestForQuotation.objects.create(
            title='Test RFQ 2',
            type=RFQType.SUPPLY,
            currency='USD',
            owner=self.user
        )
        
        url = '/procurement/api/request-quotation/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['message'], 'RFQs retrieved successfully')
        self.assertIn('data', response.data)
        self.assertGreaterEqual(len(response.data['data']), 2)
    
    def test_retrieve_rfq(self):
        """Test retrieving a single RFQ"""
        rfq = RequestForQuotation.objects.create(
            title='Test RFQ',
            type=RFQType.IFM_SERVICES,
            currency='NGN',
            owner=self.user
        )
        
        url = f'/procurement/api/request-quotation/{rfq.id}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['id'], rfq.id)
        self.assertEqual(response.data['data']['title'], 'Test RFQ')
    
    def test_update_rfq(self):
        """Test updating an RFQ"""
        rfq = RequestForQuotation.objects.create(
            title='Test RFQ',
            type=RFQType.IFM_SERVICES,
            currency='NGN',
            owner=self.user
        )
        
        url = f'/procurement/api/request-quotation/{rfq.id}/'
        data = {
            'title': 'Updated RFQ',
            'type': RFQType.SUPPLY,
            'currency': 'USD',
            'terms': 'Updated terms'
        }
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['title'], 'Updated RFQ')
    
    def test_delete_rfq(self):
        """Test deleting an RFQ"""
        rfq = RequestForQuotation.objects.create(
            title='Test RFQ',
            type=RFQType.IFM_SERVICES,
            currency='NGN',
            owner=self.user
        )
        
        url = f'/procurement/api/request-quotation/{rfq.id}/'
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertFalse(RequestForQuotation.objects.filter(id=rfq.id).exists())
    
    def test_create_rfq_validation_error(self):
        """Test RFQ creation with invalid data"""
        url = '/procurement/api/request-quotation/'
        data = {
            'title': '',  # Invalid: empty title
            'type': 'Invalid Type',  # Invalid type
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('errors', response.data)


class PurchaseOrderAPITest(ProcurementAPITestCase):
    """Test Purchase Order API endpoints"""
    
    def test_create_purchase_order(self):
        """Test creating a new Purchase Order"""
        url = '/procurement/api/purchase-orders/'
        data = {
            'type': 'Test Purchase Order',
            'facility': self.facility.id,
            'department': self.department.id,
            'requested_by': self.user.id,
            'requested_date': date.today().isoformat(),
            'vendor': self.vendor.id,
            'status': PurchaseOrderStatus.DRAFT
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['message'], 'Purchase order created successfully')
        self.assertIn('data', response.data)
    
    def test_list_purchase_orders(self):
        """Test listing Purchase Orders"""
        PurchaseOrder.objects.create(
            type='Test PO 1',
            facility=self.facility,
            department=self.department,
            requested_by=self.user,
            requested_date=date.today(),
            vendor=self.vendor,
            status=PurchaseOrderStatus.DRAFT,
            owner=self.user
        )
        PurchaseOrder.objects.create(
            type='Test PO 2',
            facility=self.facility,
            department=self.department,
            requested_by=self.user,
            requested_date=date.today(),
            vendor=self.vendor,
            status=PurchaseOrderStatus.DRAFT,
            owner=self.user
        )
        
        url = '/procurement/api/purchase-orders/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('data', response.data)
    
    def test_retrieve_purchase_order(self):
        """Test retrieving a single Purchase Order"""
        url = f'/procurement/api/purchase-orders/{self.purchase_order.id}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['id'], self.purchase_order.id)


class PurchaseOrderRequisitionAPITest(ProcurementAPITestCase):
    """Test Purchase Order Requisition API endpoints"""
    
    def test_create_requisition(self):
        """Test creating a new Purchase Requisition"""
        url = '/procurement/api/po-requisitions/'
        data = {
            'title': 'Test Requisition',
            'vendor': self.vendor.id,
            'description': 'Test description',
            'amount': '1000.00',
            'expected_delivery_date': (date.today() + timedelta(days=7)).isoformat(),
            'invoice_number': ''  # Will be auto-generated
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertIn('data', response.data)
        # Check that invoice number was auto-generated
        self.assertTrue(response.data['data']['invoice_number'].startswith('INV-'))
    
    def test_list_requisitions(self):
        """Test listing Purchase Requisitions"""
        PurchaseOrderRequisition.objects.create(
            title='Test Req 1',
            vendor=self.vendor,
            description='Test',
            amount=1000.00,
            expected_delivery_date=date.today(),
            owner=self.user
        )
        
        url = '/procurement/api/po-requisitions/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('data', response.data)
    
    def test_retrieve_requisition(self):
        """Test retrieving a single Requisition"""
        requisition = PurchaseOrderRequisition.objects.create(
            title='Test Req',
            vendor=self.vendor,
            description='Test',
            amount=1000.00,
            expected_delivery_date=date.today(),
            owner=self.user
        )
        
        url = f'/procurement/api/po-requisitions/{requisition.id}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['id'], requisition.id)
    
    def test_update_requisition(self):
        """Test updating a Requisition"""
        requisition = PurchaseOrderRequisition.objects.create(
            title='Test Req',
            vendor=self.vendor,
            description='Test',
            amount=1000.00,
            expected_delivery_date=date.today(),
            owner=self.user
        )
        
        url = f'/procurement/api/po-requisitions/{requisition.id}/'
        data = {
            'title': 'Updated Requisition',
            'amount': '2000.00'
        }
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['title'], 'Updated Requisition')


class GoodsReceivedNoteAPITest(ProcurementAPITestCase):
    """Test Goods Received Note API endpoints"""
    
    def test_create_grn(self):
        """Test creating a new GRN"""
        url = '/procurement/api/goods-received-note/'
        data = {
            'date_of_receipt': date.today().isoformat(),
            'purchase_order': self.purchase_order.id,
            'vendor': self.vendor.id,
            'facility': self.facility.id,
            'received_by': self.user.id,
            'delivery_note_number': 'DN-001',
            'invoice_number': 'INV-001'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertIn('data', response.data)
        # Check that GRN number was auto-generated
        self.assertTrue(response.data['data']['grn_number'].startswith('GRN-'))
    
    def test_list_grns(self):
        """Test listing GRNs"""
        GoodsReceivedNote.objects.create(
            date_of_receipt=date.today(),
            purchase_order=self.purchase_order,
            vendor=self.vendor,
            facility=self.facility,
            received_by=self.user,
            owner=self.user
        )
        
        url = '/procurement/api/goods-received-note/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('data', response.data)
    
    def test_retrieve_grn(self):
        """Test retrieving a single GRN"""
        grn = GoodsReceivedNote.objects.create(
            date_of_receipt=date.today(),
            purchase_order=self.purchase_order,
            vendor=self.vendor,
            facility=self.facility,
            received_by=self.user,
            owner=self.user
        )
        
        url = f'/procurement/api/goods-received-note/{grn.id}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['id'], grn.id)


class VendorContractAPITest(ProcurementAPITestCase):
    """Test Vendor Contract API endpoints"""
    
    def test_create_vendor_contract(self):
        """Test creating a new Vendor Contract"""
        url = '/procurement/api/vendor-contracts/'
        data = {
            'contract_title': 'Test Contract',
            'vendor': self.vendor.id,
            'contract_type': VendorContractType.SERVICE,
            'start_date': date.today().isoformat(),
            'end_date': (date.today() + timedelta(days=365)).isoformat(),
            'proposed_value': '50000.00',
            'reviewer': self.user.id
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertIn('data', response.data)
        self.assertEqual(response.data['data']['contract_title'], 'Test Contract')
    
    def test_list_vendor_contracts(self):
        """Test listing Vendor Contracts"""
        VendorContract.objects.create(
            contract_title='Contract 1',
            vendor=self.vendor,
            contract_type=VendorContractType.SERVICE,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
            proposed_value=50000.00,
            owner=self.user
        )
        
        url = '/procurement/api/vendor-contracts/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('data', response.data)
    
    def test_retrieve_vendor_contract(self):
        """Test retrieving a single Vendor Contract"""
        contract = VendorContract.objects.create(
            contract_title='Test Contract',
            vendor=self.vendor,
            contract_type=VendorContractType.SERVICE,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
            proposed_value=50000.00,
            owner=self.user
        )
        
        url = f'/procurement/api/vendor-contracts/{contract.id}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['id'], contract.id)
    
    def test_update_vendor_contract(self):
        """Test updating a Vendor Contract"""
        contract = VendorContract.objects.create(
            contract_title='Test Contract',
            vendor=self.vendor,
            contract_type=VendorContractType.SERVICE,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
            proposed_value=50000.00,
            owner=self.user
        )
        
        url = f'/procurement/api/vendor-contracts/{contract.id}/'
        data = {
            'contract_title': 'Updated Contract',
            'proposed_value': '75000.00'
        }
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['contract_title'], 'Updated Contract')
    
    def test_delete_vendor_contract(self):
        """Test deleting a Vendor Contract"""
        contract = VendorContract.objects.create(
            contract_title='Test Contract',
            vendor=self.vendor,
            contract_type=VendorContractType.SERVICE,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
            proposed_value=50000.00,
            owner=self.user
        )
        
        url = f'/procurement/api/vendor-contracts/{contract.id}/'
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertFalse(VendorContract.objects.filter(id=contract.id).exists())


class APIResponseFormatTest(ProcurementAPITestCase):
    """Test unified APIResponse format"""
    
    def test_success_response_format(self):
        """Test that success responses have correct format"""
        url = '/procurement/api/request-quotation/'
        response = self.client.get(url)
        
        self.assertIn('success', response.data)
        self.assertIn('message', response.data)
        self.assertIn('data', response.data)
        self.assertTrue(response.data['success'])
    
    def test_error_response_format(self):
        """Test that error responses have correct format"""
        url = '/procurement/api/request-quotation/999999/'
        response = self.client.get(url)
        
        self.assertIn('success', response.data)
        self.assertIn('message', response.data)
        self.assertFalse(response.data['success'])
    
    def test_validation_error_format(self):
        """Test that validation errors have correct format"""
        url = '/procurement/api/request-quotation/'
        data = {}  # Invalid data
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('errors', response.data)


class AuthenticationTest(TestCase):
    """Test authentication requirements"""
    
    def setUp(self):
        self.client = APIClient()
    
    def test_unauthenticated_access(self):
        """Test that unauthenticated users cannot access endpoints"""
        url = '/procurement/api/request-quotation/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
