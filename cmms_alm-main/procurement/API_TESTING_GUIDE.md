# Procurement API Testing Guide

## Overview
This document provides a guide for testing all procurement API endpoints. All endpoints use a unified `APIResponse` format.

## API Response Format

All endpoints return responses in the following format:

### Success Response
```json
{
    "success": true,
    "message": "Operation successful message",
    "data": { ... }
}
```

### Error Response
```json
{
    "success": false,
    "message": "Error message",
    "errors": { ... }
}
```

## Endpoints

### Base URL
All procurement API endpoints are prefixed with: `/procurement/api/`

### 1. Request for Quotation (RFQ)

**Base URL:** `/procurement/api/request-quotation/`

#### Create RFQ
```bash
POST /procurement/api/request-quotation/
Content-Type: application/json

{
    "title": "Test RFQ",
    "type": "IFM Services",  # Options: IFM Services, Supply, General Services, Other Services
    "currency": "NGN",
    "terms": "Test terms and conditions",
    "requester": 1,  # User ID
    "facility": 1,  # Facility ID
    "vendors": [1, 2]  # Array of Vendor IDs
}
```

#### List RFQs
```bash
GET /procurement/api/request-quotation/
```

#### Retrieve RFQ
```bash
GET /procurement/api/request-quotation/{id}/
```

#### Update RFQ
```bash
PATCH /procurement/api/request-quotation/{id}/
Content-Type: application/json

{
    "title": "Updated RFQ Title",
    "currency": "USD"
}
```

#### Delete RFQ
```bash
DELETE /procurement/api/request-quotation/{id}/
```

---

### 2. Purchase Order

**Base URL:** `/procurement/api/purchase-orders/`

#### Create Purchase Order
```bash
POST /procurement/api/purchase-orders/
Content-Type: application/json

{
    "po_number": "PO-000001",
    "type": "Test Purchase Order",
    "facility": 1,
    "department": 1,
    "requested_by": 1,
    "requested_date": "2024-01-15",
    "vendor": 1,
    "status": "Draft"  # Options: Draft, Pending, Sent, Delivered, Cancelled
}
```

#### List Purchase Orders
```bash
GET /procurement/api/purchase-orders/
```

#### Retrieve Purchase Order
```bash
GET /procurement/api/purchase-orders/{id}/
```

#### Update Purchase Order
```bash
PATCH /procurement/api/purchase-orders/{id}/
```

#### Delete Purchase Order
```bash
DELETE /procurement/api/purchase-orders/{id}/
```

---

### 3. Purchase Order Requisition

**Base URL:** `/procurement/api/po-requisitions/`

#### Create Requisition
```bash
POST /procurement/api/po-requisitions/
Content-Type: application/json

{
    "title": "Test Requisition",
    "vendor": 1,
    "description": "Test description",
    "amount": "1000.00",
    "expected_delivery_date": "2024-02-01",
    "sage_reference_number": "SAGE-001"  # Optional
    # invoice_number is auto-generated as INV-000000
}
```

**Note:** The `invoice_number` field is auto-generated with format `INV-000000` if not provided.

#### List Requisitions
```bash
GET /procurement/api/po-requisitions/
```

#### Retrieve Requisition
```bash
GET /procurement/api/po-requisitions/{id}/
```

#### Update Requisition
```bash
PATCH /procurement/api/po-requisitions/{id}/
```

#### Delete Requisition
```bash
DELETE /procurement/api/po-requisitions/{id}/
```

---

### 4. Goods Received Note (GRN)

**Base URL:** `/procurement/api/goods-received-note/`

#### Create GRN
```bash
POST /procurement/api/goods-received-note/
Content-Type: application/json

{
    "date_of_receipt": "2024-01-20",
    "purchase_order": 1,  # Purchase Order ID
    "vendor": 1,
    "facility": 1,
    "received_by": 1,  # User ID
    "delivery_note_number": "DN-001",
    "invoice_number": "INV-001"
    # grn_number is auto-generated as GRN-000000
}
```

**Note:** The `grn_number` field is auto-generated with format `GRN-000000` if not provided.

#### List GRNs
```bash
GET /procurement/api/goods-received-note/
```

#### Retrieve GRN
```bash
GET /procurement/api/goods-received-note/{id}/
```

#### Update GRN
```bash
PATCH /procurement/api/goods-received-note/{id}/
```

#### Delete GRN
```bash
DELETE /procurement/api/goods-received-note/{id}/
```

---

### 5. Vendor Contract

**Base URL:** `/procurement/api/vendor-contracts/`

#### Create Vendor Contract
```bash
POST /procurement/api/vendor-contracts/
Content-Type: application/json

{
    "contract_title": "Service Contract 2024",
    "vendor": 1,
    "contract_type": "Service",  # Options: Service, Purchase, Lease, NDA
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "proposed_value": "50000.00",
    "reviewer": 1  # User ID (optional)
}
```

#### List Vendor Contracts
```bash
GET /procurement/api/vendor-contracts/
```

#### Retrieve Vendor Contract
```bash
GET /procurement/api/vendor-contracts/{id}/
```

#### Update Vendor Contract
```bash
PATCH /procurement/api/vendor-contracts/{id}/
```

#### Delete Vendor Contract
```bash
DELETE /procurement/api/vendor-contracts/{id}/
```

---

## Testing with cURL

### Example: Create RFQ
```bash
curl -X POST http://localhost:8000/procurement/api/request-quotation/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "title": "Test RFQ",
    "type": "IFM Services",
    "currency": "NGN",
    "terms": "Test terms",
    "requester": 1,
    "facility": 1,
    "vendors": [1]
  }'
```

### Example: List RFQs
```bash
curl -X GET http://localhost:8000/procurement/api/request-quotation/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Testing with Python

Run the test suite:
```bash
python manage.py test procurement.tests --verbosity=2
```

## Authentication

All endpoints require authentication. Include the JWT token in the Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

## File Attachments

For endpoints that support file attachments (RFQ, Purchase Order, Requisition, Vendor Contract), use multipart/form-data:

```bash
curl -X POST http://localhost:8000/procurement/api/request-quotation/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "title=Test RFQ" \
  -F "type=IFM Services" \
  -F "currency=NGN" \
  -F "attachments=@/path/to/file.pdf"
```

## Expected Response Codes

- `200 OK` - Success (GET, PUT, PATCH, DELETE)
- `201 Created` - Resource created successfully (POST)
- `400 Bad Request` - Validation errors
- `401 Unauthorized` - Authentication required
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

## Notes

1. **Auto-generated Fields:**
   - `invoice_number` in PurchaseOrderRequisition: Format `INV-000000`
   - `grn_number` in GoodsReceivedNote: Format `GRN-000000`

2. **Many-to-Many Fields:**
   - `vendors` in RequestForQuotation: Pass as array of vendor IDs

3. **Foreign Key Fields:**
   - All foreign key fields accept the related object's ID

4. **Date Fields:**
   - All date fields accept ISO format: `YYYY-MM-DD`

