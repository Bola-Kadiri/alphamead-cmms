# Procurement API Documentation

## Table of Contents
1. [Overview](#overview)
2. [Base URL](#base-url)
3. [Authentication](#authentication)
4. [Unified Response Format](#unified-response-format)
5. [Endpoints](#endpoints)
   - [Request for Quotation (RFQ)](#request-for-quotation-rfq)
   - [Purchase Order](#purchase-order)
   - [Purchase Order Requisition](#purchase-order-requisition)
   - [Goods Received Note (GRN)](#goods-received-note-grn)
   - [Vendor Contract](#vendor-contract)
6. [Error Handling](#error-handling)
7. [Enums](#enums)

---

## Overview

The Procurement API provides a comprehensive set of endpoints for managing procurement-related operations including Request for Quotation (RFQ), Purchase Orders, Purchase Order Requisitions, Goods Received Notes (GRN), and Vendor Contracts.

All endpoints use a unified response format and require authentication.

---

## Base URL

```
/procurement/api/
```

---

## Authentication

All endpoints require authentication. Include the JWT token in the Authorization header:

```
Authorization: Bearer <your_jwt_token>
```

To obtain a token, use the authentication endpoint:
```
POST /auth/token/
```

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

---

## Unified Response Format

All API responses follow a consistent structure:

### Success Response
```json
{
  "success": true,
  "message": "Operation successful message",
  "data": {
    // Response data here
  }
}
```

### Error Response
```json
{
  "success": false,
  "message": "Error message",
  "errors": {
    // Field-specific errors (for validation errors)
  }
}
```

### Response Status Codes
- `200 OK` - Successful GET, PUT, PATCH, DELETE requests
- `201 Created` - Successful POST requests (resource created)
- `400 Bad Request` - Validation errors or bad request data
- `401 Unauthorized` - Missing or invalid authentication token
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

---

## Endpoints

### Request for Quotation (RFQ)

#### List RFQs
**GET** `/procurement/api/request-quotation/`

**Response:**
```json
{
  "success": true,
  "message": "RFQs retrieved successfully",
  "data": [
    {
      "id": 1,
      "type": "IFM Services",
      "title": "Office Cleaning Services",
      "currency": "NGN",
      "terms": "Payment within 30 days",
      "requester": 1,
      "requester_detail": {
        "id": 1,
        "email": "user@example.com",
        "first_name": "John",
        "last_name": "Doe"
      },
      "facility": 1,
      "facility_detail": {
        "id": 1,
        "name": "Main Facility",
        "code": "00001"
      },
      "vendors": [1, 2],
      "vendors_detail": [
        {
          "id": 1,
          "name": "ABC Cleaning Services",
          "type": "Company"
        }
      ],
      "attachments_data": [],
      "created_at": "2025-01-10T10:00:00Z",
      "updated_at": "2025-01-10T10:00:00Z"
    }
  ]
}
```

#### Retrieve RFQ
**GET** `/procurement/api/request-quotation/{id}/`

**Response:**
```json
{
  "success": true,
  "message": "RFQ retrieved successfully",
  "data": {
    "id": 1,
    "type": "IFM Services",
    "title": "Office Cleaning Services",
    // ... same structure as list item
  }
}
```

#### Create RFQ
**POST** `/procurement/api/request-quotation/`

**Request Body:**
```json
{
  "type": "IFM Services",
  "title": "Office Cleaning Services",
  "currency": "NGN",
  "terms": "Payment within 30 days",
  "requester": 1,
  "facility": 1,
  "vendors": [1, 2],
  "attachments": []  // Optional: array of file objects
}
```

**Valid `type` values:**
- `"IFM Services"`
- `"Supply"`
- `"General Services"`
- `"Other Services"`

**Response:**
```json
{
  "success": true,
  "message": "RFQ created successfully",
  "data": {
    "id": 1,
    "type": "IFM Services",
    "title": "Office Cleaning Services",
    // ... full RFQ object
  }
}
```

#### Update RFQ
**PUT/PATCH** `/procurement/api/request-quotation/{id}/`

**Request Body:** (same as create, all fields optional for PATCH)

**Response:**
```json
{
  "success": true,
  "message": "RFQ updated successfully",
  "data": {
    // Updated RFQ object
  }
}
```

#### Delete RFQ
**DELETE** `/procurement/api/request-quotation/{id}/`

**Response:**
```json
{
  "success": true,
  "message": "RFQ deleted successfully"
}
```

---

### Purchase Order

#### List Purchase Orders
**GET** `/procurement/api/purchase-orders/`

**Response:**
```json
{
  "success": true,
  "message": "Purchase orders retrieved successfully",
  "data": [
    {
      "id": 1,
      "type": "Equipment Purchase",
      "facility": 1,
      "facility_detail": {
        "id": 1,
        "name": "Main Facility"
      },
      "department": 1,
      "department_detail": {
        "id": 1,
        "name": "IT Department"
      },
      "requested_by": 1,
      "requested_by_detail": {
        "id": 1,
        "email": "user@example.com"
      },
      "requested_date": "2025-01-10",
      "vendor": 1,
      "vendor_detail": {
        "id": 1,
        "name": "ABC Suppliers"
      },
      "contact_person": "John Smith",
      "expected_delivery_date": "2025-01-20",
      "ship_to": "123 Main St, City",
      "terms_and_conditions": "Standard terms apply",
      "status": "Draft",
      "items": [],
      "comments": [],
      "approvals": [],
      "created_at": "2025-01-10T10:00:00Z",
      "updated_at": "2025-01-10T10:00:00Z"
    }
  ]
}
```

#### Retrieve Purchase Order
**GET** `/procurement/api/purchase-orders/{id}/`

**Response:**
```json
{
  "success": true,
  "message": "Purchase order retrieved successfully",
  "data": {
    // Full purchase order object
  }
}
```

#### Create Purchase Order
**POST** `/procurement/api/purchase-orders/`

**Request Body:**
```json
{
  "type": "Equipment Purchase",
  "facility": 1,
  "department": 1,
  "requested_by": 1,
  "requested_date": "2025-01-10",
  "vendor": 1,
  "contact_person": "John Smith",
  "expected_delivery_date": "2025-01-20",
  "ship_to": "123 Main St, City",
  "terms_and_conditions": "Standard terms apply",
  "status": "Draft"
}
```

**Valid `status` values:**
- `"Draft"`
- `"Pending"`
- `"Sent"`
- `"Delivered"`
- `"Cancelled"`

**Response:**
```json
{
  "success": true,
  "message": "Purchase order created successfully",
  "data": {
    // Created purchase order object
  }
}
```

#### Update Purchase Order
**PUT/PATCH** `/procurement/api/purchase-orders/{id}/`

**Request Body:** (same as create, all fields optional for PATCH)

**Response:**
```json
{
  "success": true,
  "message": "Purchase order updated successfully",
  "data": {
    // Updated purchase order object
  }
}
```

#### Delete Purchase Order
**DELETE** `/procurement/api/purchase-orders/{id}/`

**Response:**
```json
{
  "success": true,
  "message": "Purchase order deleted successfully"
}
```

---

### Purchase Order Requisition

#### List Purchase Order Requisitions
**GET** `/procurement/api/po-requisitions/`

**Response:**
```json
{
  "success": true,
  "message": "Purchase requisitions retrieved successfully",
  "data": [
    {
      "id": 1,
      "title": "Office Supplies Requisition",
      "vendor": 1,
      "vendor_detail": {
        "id": 1,
        "name": "ABC Suppliers"
      },
      "invoice_number": "INV-000001",
      "sage_reference_number": "SAGE-12345",
      "description": "Monthly office supplies",
      "amount": "50000.00",
      "expected_delivery_date": "2025-01-20",
      "created_at": "2025-01-10T10:00:00Z",
      "updated_at": "2025-01-10T10:00:00Z"
    }
  ]
}
```

#### Retrieve Purchase Order Requisition
**GET** `/procurement/api/po-requisitions/{id}/`

**Response:**
```json
{
  "success": true,
  "message": "Purchase requisition retrieved successfully",
  "data": {
    // Full requisition object
  }
}
```

#### Create Purchase Order Requisition
**POST** `/procurement/api/po-requisitions/`

**Request Body:**
```json
{
  "title": "Office Supplies Requisition",
  "vendor": 1,
  "sage_reference_number": "SAGE-12345",
  "description": "Monthly office supplies",
  "amount": "50000.00",
  "expected_delivery_date": "2025-01-20"
}
```

**Note:** The `invoice_number` field is auto-generated with format `INV-000000` if not provided.

**Response:**
```json
{
  "success": true,
  "message": "Purchase requisition created successfully",
  "data": {
    "id": 1,
    "title": "Office Supplies Requisition",
    "invoice_number": "INV-000001",
    // ... full requisition object
  }
}
```

#### Update Purchase Order Requisition
**PUT/PATCH** `/procurement/api/po-requisitions/{id}/`

**Request Body:** (same as create, all fields optional for PATCH)

**Response:**
```json
{
  "success": true,
  "message": "Purchase requisition updated successfully",
  "data": {
    // Updated requisition object
  }
}
```

#### Delete Purchase Order Requisition
**DELETE** `/procurement/api/po-requisitions/{id}/`

**Response:**
```json
{
  "success": true,
  "message": "Purchase requisition deleted successfully"
}
```

---

### Goods Received Note (GRN)

#### List GRNs
**GET** `/procurement/api/goods-received-note/`

**Response:**
```json
{
  "success": true,
  "message": "GRNs retrieved successfully",
  "data": [
    {
      "id": 1,
      "grn_number": "GRN-000001",
      "date_of_receipt": "2025-01-15",
      "purchase_order": 1,
      "purchase_order_detail": {
        "id": 1,
        "type": "Equipment Purchase"
      },
      "vendor": 1,
      "vendor_detail": {
        "id": 1,
        "name": "ABC Suppliers"
      },
      "delivery_note_number": "DN-001",
      "invoice_number": "INV-001",
      "facility": 1,
      "facility_detail": {
        "id": 1,
        "name": "Main Facility"
      },
      "received_by": 1,
      "received_by_detail": {
        "id": 1,
        "email": "user@example.com"
      },
      "created_at": "2025-01-15T10:00:00Z",
      "updated_at": "2025-01-15T10:00:00Z"
    }
  ]
}
```

#### Retrieve GRN
**GET** `/procurement/api/goods-received-note/{id}/`

**Response:**
```json
{
  "success": true,
  "message": "GRN retrieved successfully",
  "data": {
    // Full GRN object
  }
}
```

#### Create GRN
**POST** `/procurement/api/goods-received-note/`

**Request Body:**
```json
{
  "date_of_receipt": "2025-01-15",
  "purchase_order": 1,
  "vendor": 1,
  "delivery_note_number": "DN-001",
  "invoice_number": "INV-001",
  "facility": 1,
  "received_by": 1
}
```

**Note:** The `grn_number` field is auto-generated with format `GRN-000000` if not provided.

**Response:**
```json
{
  "success": true,
  "message": "GRN created successfully",
  "data": {
    "id": 1,
    "grn_number": "GRN-000001",
    // ... full GRN object
  }
}
```

#### Update GRN
**PUT/PATCH** `/procurement/api/goods-received-note/{id}/`

**Request Body:** (same as create, all fields optional for PATCH)

**Response:**
```json
{
  "success": true,
  "message": "GRN updated successfully",
  "data": {
    // Updated GRN object
  }
}
```

#### Delete GRN
**DELETE** `/procurement/api/goods-received-note/{id}/`

**Response:**
```json
{
  "success": true,
  "message": "GRN deleted successfully"
}
```

---

### Vendor Contract

#### List Vendor Contracts
**GET** `/procurement/api/vendor-contracts/`

**Response:**
```json
{
  "success": true,
  "message": "Vendor contracts retrieved successfully",
  "data": [
    {
      "id": 1,
      "contract_title": "Annual Maintenance Contract",
      "vendor": 1,
      "vendor_detail": {
        "id": 1,
        "name": "ABC Services"
      },
      "contract_type": "Service",
      "start_date": "2025-01-01",
      "end_date": "2025-12-31",
      "proposed_value": "500000.00",
      "reviewer": 1,
      "reviewer_detail": {
        "id": 1,
        "email": "reviewer@example.com"
      },
      "agreement_data": [],
      "created_at": "2025-01-01T10:00:00Z",
      "updated_at": "2025-01-01T10:00:00Z"
    }
  ]
}
```

#### Retrieve Vendor Contract
**GET** `/procurement/api/vendor-contracts/{id}/`

**Response:**
```json
{
  "success": true,
  "message": "Vendor contract retrieved successfully",
  "data": {
    // Full vendor contract object
  }
}
```

#### Create Vendor Contract
**POST** `/procurement/api/vendor-contracts/`

**Request Body:**
```json
{
  "contract_title": "Annual Maintenance Contract",
  "vendor": 1,
  "contract_type": "Service",
  "start_date": "2025-01-01",
  "end_date": "2025-12-31",
  "proposed_value": "500000.00",
  "reviewer": 1,
  "agreements": []  // Optional: array of file objects
}
```

**Valid `contract_type` values:**
- `"Service"`
- `"Purchase"`
- `"Lease"`
- `"NDA"`

**Response:**
```json
{
  "success": true,
  "message": "Vendor contract created successfully",
  "data": {
    // Created vendor contract object
  }
}
```

#### Update Vendor Contract
**PUT/PATCH** `/procurement/api/vendor-contracts/{id}/`

**Request Body:** (same as create, all fields optional for PATCH)

**Response:**
```json
{
  "success": true,
  "message": "Vendor contract updated successfully",
  "data": {
    // Updated vendor contract object
  }
}
```

#### Delete Vendor Contract
**DELETE** `/procurement/api/vendor-contracts/{id}/`

**Response:**
```json
{
  "success": true,
  "message": "Vendor contract deleted successfully"
}
```

---

## Error Handling

### Validation Error (400)
```json
{
  "success": false,
  "message": "Failed to create RFQ",
  "errors": {
    "title": ["This field is required."],
    "type": ["Invalid choice."]
  }
}
```

### Not Found Error (404)
```json
{
  "success": false,
  "message": "RFQ not found",
  "errors": {}
}
```

### Unauthorized Error (401)
```json
{
  "success": false,
  "message": "Authentication credentials were not provided.",
  "errors": {}
}
```

### Forbidden Error (403)
```json
{
  "success": false,
  "message": "You do not have permission to perform this action.",
  "errors": {}
}
```

### Internal Server Error (500)
```json
{
  "success": false,
  "message": "Error retrieving RFQs: <error details>",
  "errors": {}
}
```

---

## Enums

### RFQ Type
- `"IFM Services"` - IFM Services
- `"Supply"` - Supply
- `"General Services"` - General Services
- `"Other Services"` - Other Services

### Purchase Order Status
- `"Draft"` - Draft
- `"Pending"` - Pending
- `"Sent"` - Sent
- `"Delivered"` - Delivered
- `"Cancelled"` - Cancelled

### Vendor Contract Type
- `"Service"` - Service
- `"Purchase"` - Purchase
- `"Lease"` - Lease
- `"NDA"` - NDA

---

## Auto-Generated Fields

### Invoice Number (Purchase Order Requisition)
- Format: `INV-000000` (6-digit zero-padded number)
- Auto-generated if not provided during creation
- Example: `INV-000001`, `INV-000002`, etc.

### GRN Number (Goods Received Note)
- Format: `GRN-000000` (6-digit zero-padded number)
- Auto-generated if not provided during creation
- Example: `GRN-000001`, `GRN-000002`, etc.

---

## Pagination

List endpoints support pagination. Paginated responses include pagination metadata:

```json
{
  "success": true,
  "message": "RFQs retrieved successfully",
  "data": {
    "count": 100,
    "next": "/procurement/api/request-quotation/?page=2",
    "previous": null,
    "results": [
      // Array of RFQ objects
    ]
  }
}
```

---

## Notes

1. **File Attachments**: For endpoints that support file attachments (RFQ, Vendor Contract), use multipart/form-data format when uploading files.

2. **Date Format**: All date fields should be in ISO 8601 format: `YYYY-MM-DD` (e.g., `2025-01-10`).

3. **Decimal Fields**: Amount and value fields should be provided as strings with decimal notation (e.g., `"50000.00"`).

4. **Foreign Keys**: When creating or updating resources, provide the ID of the related object (e.g., `"vendor": 1`).

5. **Many-to-Many Fields**: Provide arrays of IDs (e.g., `"vendors": [1, 2, 3]`).

6. **Read-Only Fields**: Fields like `id`, `created_at`, `updated_at`, and detail fields (e.g., `vendor_detail`) are read-only and cannot be set via API.

---

## Example cURL Requests

### Create RFQ
```bash
curl -X POST "http://localhost:8000/procurement/api/request-quotation/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "IFM Services",
    "title": "Office Cleaning Services",
    "currency": "NGN",
    "terms": "Payment within 30 days",
    "requester": 1,
    "facility": 1,
    "vendors": [1, 2]
  }'
```

### List Purchase Orders
```bash
curl -X GET "http://localhost:8000/procurement/api/purchase-orders/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Update Purchase Order Requisition
```bash
curl -X PATCH "http://localhost:8000/procurement/api/po-requisitions/1/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "75000.00"
  }'
```

---

## Support

For issues or questions regarding the Procurement API, please contact the development team.

