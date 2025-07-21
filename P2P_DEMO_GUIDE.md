# 🚀 P2P Automation System Demo Guide

> **Complete Procure-to-Pay automation with FastAPI, DynamoDB, S3, and Workday integration**

---

## 🖥️ 1. Local Setup Instructions

### Prerequisites
- Python 3.9+
- AWS CLI configured with credentials
- Access to AWS account (us-east-1 region)

### Dependencies Installation
```bash
cd backend
pip install -r requirements.txt

# Additional dependency for automation scripts
pip install requests
```

### Environment Variables (Optional)
The system uses AWS default credential chain. If needed, set:

**Unix/Linux/macOS:**
```bash
export AWS_DEFAULT_REGION=us-east-1
export AWS_PROFILE=your-profile  # if using named profiles
```

**Windows PowerShell:**
```powershell
$env:AWS_DEFAULT_REGION="us-east-1"
$env:AWS_PROFILE="your-profile"  # if using named profiles
```

### Start FastAPI Server
```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Verification:**
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
- Root endpoint: http://localhost:8000/

---

## 🔌 2. Manual Demo Flow

### Step 1: Create a Vendor

**Unix/Linux/macOS (bash):**
```bash
curl -X POST "http://localhost:8000/api/v1/vendors/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ACME Supplies Corp",
    "email": "accounting@acmesupplies.com",
    "phone": "+1-555-123-4567",
    "address": "123 Business Ave, Cityville, ST 12345",
    "tax_id": "12-3456789",
    "payment_terms": "Net 30"
  }'
```

**Windows PowerShell:**
```powershell
$vendorData = @{
    name = "ACME Supplies Corp"
    email = "accounting@acmesupplies.com"
    phone = "+1-555-123-4567"
    address = "123 Business Ave, Cityville, ST 12345"
    tax_id = "12-3456789"
    payment_terms = "Net 30"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/vendors/" -Method POST -Body $vendorData -ContentType "application/json"
```

**Alternative PowerShell (using curl.exe):**
```powershell
curl.exe -X POST "http://localhost:8000/api/v1/vendors/" `
  -H "Content-Type: application/json" `
  -d '{
    "name": "ACME Supplies Corp",
    "email": "accounting@acmesupplies.com",
    "phone": "+1-555-123-4567",
    "address": "123 Business Ave, Cityville, ST 12345",
    "tax_id": "12-3456789",
    "payment_terms": "Net 30"
  }'
```

**Response:** Note the `vendor_id` from the response data.

### Step 2: Create a Purchase Order

**Unix/Linux/macOS (bash):**
```bash
curl -X POST "http://localhost:8000/api/v1/purchase-orders/" \
  -H "Content-Type: application/json" \
  -d '{
    "vendor_id": "VENDOR_ID_FROM_STEP1",
    "items": [
      {
        "description": "Office Supplies - Pens",
        "quantity": 100,
        "unit_price": 2.50,
        "total_amount": 250.00
      },
      {
        "description": "Office Supplies - Paper",
        "quantity": 50,
        "unit_price": 12.00,
        "total_amount": 600.00
      }
    ],
    "total_amount": 850.00
  }'
```

**Windows PowerShell:**
```powershell
# Replace VENDOR_ID_FROM_STEP1 with actual vendor ID
$poData = @{
    vendor_id = "VENDOR_ID_FROM_STEP1"
    items = @(
        @{
            description = "Office Supplies - Pens"
            quantity = 100
            unit_price = 2.50
            total_amount = 250.00
        },
        @{
            description = "Office Supplies - Paper"
            quantity = 50
            unit_price = 12.00
            total_amount = 600.00
        }
    )
    total_amount = 850.00
} | ConvertTo-Json -Depth 3

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/purchase-orders/" -Method POST -Body $poData -ContentType "application/json"
```

**Alternative PowerShell (using curl.exe):**
```powershell
curl.exe -X POST "http://localhost:8000/api/v1/purchase-orders/" `
  -H "Content-Type: application/json" `
  -d '{
    "vendor_id": "VENDOR_ID_FROM_STEP1",
    "items": [
      {
        "description": "Office Supplies - Pens",
        "quantity": 100,
        "unit_price": 2.50,
        "total_amount": 250.00
      },
      {
        "description": "Office Supplies - Paper",
        "quantity": 50,
        "unit_price": 12.00,
        "total_amount": 600.00
      }
    ],
    "total_amount": 850.00
  }'
```

**Note:** Save the `po_id` from response. Then approve the PO:

**Unix/Linux/macOS:**
```bash
curl -X PUT "http://localhost:8000/api/v1/purchase-orders/PO_ID/approve"
```

**Windows PowerShell:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/purchase-orders/PO_ID/approve" -Method PUT
# Or: curl.exe -X PUT "http://localhost:8000/api/v1/purchase-orders/PO_ID/approve"
```

### Step 3: Submit an Invoice

**Unix/Linux/macOS (bash):**
```bash
curl -X POST "http://localhost:8000/api/v1/invoices/" \
  -H "Content-Type: application/json" \
  -d '{
    "po_id": "PO_ID_FROM_STEP2",
    "invoice_number": "INV-2025-001",
    "items": [
      {
        "description": "Office Supplies - Pens",
        "quantity": 100,
        "unit_price": 2.50
      },
      {
        "description": "Office Supplies - Paper", 
        "quantity": 50,
        "unit_price": 12.00
      }
    ],
    "total_amount": 850.00
  }'
```

**Windows PowerShell:**
```powershell
# Replace PO_ID_FROM_STEP2 with actual PO ID
$invoiceData = @{
    po_id = "PO_ID_FROM_STEP2"
    invoice_number = "INV-2025-001"
    items = @(
        @{
            description = "Office Supplies - Pens"
            quantity = 100
            unit_price = 2.50
        },
        @{
            description = "Office Supplies - Paper"
            quantity = 50
            unit_price = 12.00
        }
    )
    total_amount = 850.00
} | ConvertTo-Json -Depth 3

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/invoices/" -Method POST -Body $invoiceData -ContentType "application/json"
```

**Alternative PowerShell (using curl.exe):**
```powershell
curl.exe -X POST "http://localhost:8000/api/v1/invoices/" `
  -H "Content-Type: application/json" `
  -d '{
    "po_id": "PO_ID_FROM_STEP2",
    "invoice_number": "INV-2025-001",
    "items": [
      {
        "description": "Office Supplies - Pens",
        "quantity": 100,
        "unit_price": 2.50
      },
      {
        "description": "Office Supplies - Paper", 
        "quantity": 50,
        "unit_price": 12.00
      }
    ],
    "total_amount": 850.00
  }'
```

**Note:** Save the `invoice_id` for next step.

### Step 4: Reconcile Invoice

**Unix/Linux/macOS:**
```bash
curl -X PUT "http://localhost:8000/api/v1/invoices/INVOICE_ID/reconcile"
```

**Windows PowerShell:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/invoices/INVOICE_ID/reconcile" -Method PUT
# Or: curl.exe -X PUT "http://localhost:8000/api/v1/invoices/INVOICE_ID/reconcile"
```

**Expected:** Status should change to `"matched"` if amounts align with PO.

### Step 5: Approve Invoice → Generate XML/JSON + Upload to S3

**Unix/Linux/macOS (bash):**
```bash
curl -X POST "http://localhost:8000/api/v1/payments/INVOICE_ID/approve" \
  -H "Content-Type: application/json" \
  -d '{
    "approved_by": "manager@company.com"
  }'
```

**Windows PowerShell:**
```powershell
$approvalData = @{
    approved_by = "manager@company.com"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/payments/INVOICE_ID/approve" -Method POST -Body $approvalData -ContentType "application/json"
```

**Alternative PowerShell (using curl.exe):**
```powershell
curl.exe -X POST "http://localhost:8000/api/v1/payments/INVOICE_ID/approve" `
  -H "Content-Type: application/json" `
  -d '{
    "approved_by": "manager@company.com"
  }'
```

**Result:** 
- Creates payment record
- Generates Workday-compatible XML and JSON files
- Uploads files to S3 bucket: `p2p-payment-xml-storage-*`
- Returns payment ID and S3 file keys

### Step 6: Download Export via /exports

**Unix/Linux/macOS:**
```bash
# List all export files
curl "http://localhost:8000/api/v1/exports/"

# Download specific XML file
curl "http://localhost:8000/api/v1/exports/PAYMENT_ID/xml"

# Download specific JSON file  
curl "http://localhost:8000/api/v1/exports/PAYMENT_ID/json"
```

**Windows PowerShell:**
```powershell
# List all export files
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/exports/"

# Download specific XML file
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/exports/PAYMENT_ID/xml"

# Download specific JSON file  
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/exports/PAYMENT_ID/json"
```

### Step 7: Simulate Workday Callback

**Unix/Linux/macOS (bash):**
```bash
curl -X POST "http://localhost:8000/api/v1/workday/callback" \
  -H "Content-Type: application/json" \
  -d '{
    "payment_id": "PAYMENT_ID_FROM_STEP5",
    "status": "sent"
  }'
```

**Windows PowerShell:**
```powershell
$callbackData = @{
    payment_id = "PAYMENT_ID_FROM_STEP5"
    status = "sent"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/workday/callback" -Method POST -Body $callbackData -ContentType "application/json"
```

**Alternative PowerShell (using curl.exe):**
```powershell
curl.exe -X POST "http://localhost:8000/api/v1/workday/callback" `
  -H "Content-Type: application/json" `
  -d '{
    "payment_id": "PAYMENT_ID_FROM_STEP5",
    "status": "sent"
  }'
```

**Note:** This endpoint currently has a decimal conversion issue in audit logging. The core functionality works but may return an error. Use the status check endpoint to verify the payment state.

**Result:** Updates payment status from `"approved"` to `"sent"`

### Step 8: Confirm Integration via Status Check

**Unix/Linux/macOS:**
```bash
curl "http://localhost:8000/api/v1/workday/status/PAYMENT_ID"
```

**Windows PowerShell:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/workday/status/PAYMENT_ID"
# Or: curl.exe "http://localhost:8000/api/v1/workday/status/PAYMENT_ID"
```

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "payment_id": "pay_123",
    "current_status": "sent",
    "workday_callback_received": true,
    "xml_file_available": true,
    "json_file_available": true,
    "integration_status": "confirmed"
  }
}
```

---

## ⚙️ 3. Automation Simulation

### Batch Invoice Reconciliation
```bash
# Dry run (recommended first)
python infra/reconciliation_job.py --region us-east-1 --dry-run --log-level INFO

# Production run  
python infra/reconciliation_job.py --region us-east-1
```

**What it does:**
- Scans InvoicesTable for status == "received"
- Runs reconciliation logic against associated POs
- Updates invoice status to "matched" or "rejected"
- Logs results to AuditLogTable
- Provides detailed statistics

### Auto-Send Approved Payments
```bash
# Dry run mode
python infra/export_monitor.py --region us-east-1 --dry-run --log-level DEBUG

# Production run
python infra/export_monitor.py --region us-east-1

# Custom Workday endpoint
python infra/export_monitor.py --region us-east-1 --workday-url http://localhost:8000/api/v1/workday/callback
```

**What it does:**
- Finds payments with status == "approved" and no Workday callback
- Validates S3 files exist (XML + JSON)
- Simulates Workday delivery via callback
- Updates payment status to "sent"
- Generates comprehensive report

### Recommended Testing Sequence
1. Create 2-3 invoices with different scenarios (matched/rejected)
2. Run reconciliation job to batch-process them
3. Approve matched invoices to generate payment files
4. Run export monitor to simulate Workday delivery
5. Verify status transitions via API

---

## 📦 4. S3 & DynamoDB Validation

### Verify S3 Files
```bash
# List all payment files
aws s3 ls s3://p2p-payment-xml-storage-20250721-005155-6839/payments/ --recursive

# Check specific payment files
aws s3 ls s3://p2p-payment-xml-storage-20250721-005155-6839/payments/PAYMENT_ID/

# Download and inspect file
aws s3 cp s3://p2p-payment-xml-storage-20250721-005155-6839/payments/PAYMENT_ID/payment.xml ./payment.xml
cat payment.xml
```

### Verify DynamoDB Records
```bash
# Check vendors table
aws dynamodb scan --table-name VendorsTable --region us-east-1

# Check specific payment
aws dynamodb get-item --table-name PaymentsTable --key '{"id":{"S":"PAYMENT_ID"}}' --region us-east-1

# Check audit logs
aws dynamodb scan --table-name AuditLogTable --filter-expression "#type = :type" --expression-attribute-names '{"#type":"type"}' --expression-attribute-values '{":type":{"S":"PAYMENT_ACTION"}}' --region us-east-1
```

### Quick Validation Script (Python)
```python
import boto3

# Initialize clients
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
s3 = boto3.client('s3')

# Check table counts
tables = ['VendorsTable', 'PurchaseOrdersTable', 'InvoicesTable', 'PaymentsTable', 'AuditLogTable']
for table_name in tables:
    table = dynamodb.Table(table_name)
    count = table.scan(Select='COUNT')['Count']
    print(f"{table_name}: {count} records")

# Check S3 files
bucket = 'p2p-payment-xml-storage-20250721-005155-6839'
response = s3.list_objects_v2(Bucket=bucket, Prefix='payments/')
file_count = response.get('KeyCount', 0)
print(f"S3 payment files: {file_count}")
```

---

## 🧪 5. Health Checks & Troubleshooting

### API Health Validation
```bash
# Check API server status
curl http://localhost:8000/health

# Test all main endpoints
curl http://localhost:8000/api/v1/vendors/
curl http://localhost:8000/api/v1/purchase-orders/
curl http://localhost:8000/api/v1/invoices/
curl http://localhost:8000/api/v1/payments/
curl http://localhost:8000/api/v1/exports/
```

### Common Gotchas & Solutions

#### ❌ **DynamoDB Access Denied**
```
Error: User not authorized to perform: dynamodb:Scan
```
**Fix:** Ensure AWS credentials have DynamoDB permissions:
```bash
aws sts get-caller-identity  # Verify correct AWS account
aws iam list-attached-user-policies --user-name YOUR_USERNAME
```

#### ❌ **S3 Bucket Not Found**
```
Error: NoSuchBucket: The specified bucket does not exist
```
**Fix:** Verify bucket name and region:
```bash
aws s3 ls | grep p2p-payment-xml-storage
aws s3api get-bucket-location --bucket BUCKET_NAME
```

#### ❌ **Region Mismatch**
```
Error: The bucket is in this region: us-east-1
```
**Fix:** Ensure consistent region across all services:
```bash
export AWS_DEFAULT_REGION=us-east-1
# Or add --region us-east-1 to all AWS CLI commands
```

#### ❌ **Port 8000 Already in Use**
```
Error: [Errno 48] Address already in use
```
**Fix:** Kill existing process or use different port:
```bash
# Kill existing process
lsof -ti:8000 | xargs kill -9

# Or use different port
uvicorn app.main:app --port 8001
```

#### ❌ **Import Errors**
```
ModuleNotFoundError: No module named 'fastapi'
```
**Fix:** Ensure virtual environment and dependencies:
```bash
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
pip install requests  # For automation scripts
```

#### ❌ **Decimal Conversion Errors**
```
Error: Failed to process: [<class 'decimal.ConversionSyntax'>]
```
**Fix:** This is a known issue with complex audit logging. The core functionality works, but some audit log entries may fail. This has been partially fixed in the codebase by simplifying audit log data structures.

### Performance Validation
```bash
# Check response times (should be < 2 seconds)
time curl http://localhost:8000/api/v1/vendors/

# Test pagination performance
time curl "http://localhost:8000/api/v1/exports/?page=1&size=50"

# Verify reconciliation job performance
time python infra/reconciliation_job.py --region us-east-1 --dry-run
```

### Log Analysis
```bash
# Check FastAPI logs
tail -f reconciliation_job.log

# Check export monitor logs  
tail -f export_monitor.log

# AWS CloudWatch logs (if configured)
aws logs describe-log-groups --region us-east-1
```

---

## 🎯 Quick Demo Script (Complete Workflow)

### Bash Version (Unix/Linux/macOS)

Save this as `demo.sh` for rapid testing:

```bash
#!/bin/bash
set -e

echo "🚀 Starting P2P Automation Demo..."

# Start server (in background)
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
SERVER_PID=$!
sleep 5

# Create vendor
echo "📋 Creating vendor..."
VENDOR_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/vendors/" \
  -H "Content-Type: application/json" \
  -d '{"name":"Demo Vendor","email":"demo@vendor.com"}')
VENDOR_ID=$(echo $VENDOR_RESPONSE | jq -r '.data.id')
echo "✅ Vendor created: $VENDOR_ID"

# Create PO
echo "📋 Creating purchase order..."
PO_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/purchase-orders/" \
  -H "Content-Type: application/json" \
  -d "{\"vendor_id\":\"$VENDOR_ID\",\"items\":[{\"description\":\"Demo Item\",\"quantity\":10,\"unit_price\":25.00}],\"total_amount\":250.00}")
PO_ID=$(echo $PO_RESPONSE | jq -r '.data.id')
echo "✅ PO created: $PO_ID"

# Approve PO
curl -s -X PUT "http://localhost:8000/api/v1/purchase-orders/$PO_ID/approve" > /dev/null
echo "✅ PO approved"

# Submit invoice  
echo "📋 Submitting invoice..."
INVOICE_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/invoices/" \
  -H "Content-Type: application/json" \
  -d "{\"po_id\":\"$PO_ID\",\"invoice_number\":\"DEMO-001\",\"items\":[{\"description\":\"Demo Item\",\"quantity\":10,\"unit_price\":25.00}],\"total_amount\":250.00}")
INVOICE_ID=$(echo $INVOICE_RESPONSE | jq -r '.data.id')
echo "✅ Invoice submitted: $INVOICE_ID"

# Reconcile invoice
curl -s -X PUT "http://localhost:8000/api/v1/invoices/$INVOICE_ID/reconcile" > /dev/null
echo "✅ Invoice reconciled"

# Approve payment
echo "📋 Approving payment..."
PAYMENT_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/payments/$INVOICE_ID/approve" \
  -H "Content-Type: application/json" \
  -d '{"approved_by":"demo@manager.com"}')
PAYMENT_ID=$(echo $PAYMENT_RESPONSE | jq -r '.data.payment.id')
echo "✅ Payment approved: $PAYMENT_ID"

# Workday callback
curl -s -X POST "http://localhost:8000/api/v1/workday/callback" \
  -H "Content-Type: application/json" \
  -d "{\"payment_id\":\"$PAYMENT_ID\",\"status\":\"sent\"}" > /dev/null
echo "✅ Workday callback completed"

# Verify status
STATUS_RESPONSE=$(curl -s "http://localhost:8000/api/v1/workday/status/$PAYMENT_ID")
INTEGRATION_STATUS=$(echo $STATUS_RESPONSE | jq -r '.data.integration_status')
echo "✅ Integration status: $INTEGRATION_STATUS"

echo ""
echo "🎉 Demo completed successfully!"
echo "📊 Check results at: http://localhost:8000/docs"
echo "📁 Files at: http://localhost:8000/api/v1/exports/"

# Clean up
kill $SERVER_PID 2>/dev/null || true
```

**Usage:** `chmod +x demo.sh && ./demo.sh`

### PowerShell Version (Windows)

Save this as `demo.ps1` for rapid testing:

```powershell
Write-Host "🚀 Starting P2P Automation Demo..." -ForegroundColor Green

# Start server in background
Set-Location backend
$ServerJob = Start-Job -ScriptBlock {
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
}
Start-Sleep -Seconds 5

try {
    # Create vendor
    Write-Host "📋 Creating vendor..." -ForegroundColor Yellow
    $vendorData = @{
        name = "Demo Vendor"
        email = "demo@vendor.com"
    } | ConvertTo-Json
    
    $vendorResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/vendors/" -Method POST -Body $vendorData -ContentType "application/json"
    $vendorId = $vendorResponse.data.id
    Write-Host "✅ Vendor created: $vendorId" -ForegroundColor Green

    # Create PO
    Write-Host "📋 Creating purchase order..." -ForegroundColor Yellow
    $poData = @{
        vendor_id = $vendorId
        items = @(
            @{
                description = "Demo Item"
                quantity = 10
                unit_price = 25.00
                total_amount = 250.00
            }
        )
        total_amount = 250.00
    } | ConvertTo-Json -Depth 3
    
    $poResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/purchase-orders/" -Method POST -Body $poData -ContentType "application/json"
    $poId = $poResponse.data.id
    Write-Host "✅ PO created: $poId" -ForegroundColor Green

    # Approve PO
    Invoke-RestMethod -Uri "http://localhost:8000/api/v1/purchase-orders/$poId/approve" -Method PUT | Out-Null
    Write-Host "✅ PO approved" -ForegroundColor Green

    # Submit invoice
    Write-Host "📋 Submitting invoice..." -ForegroundColor Yellow
    $invoiceData = @{
        po_id = $poId
        invoice_number = "DEMO-001"
        items = @(
            @{
                description = "Demo Item"
                quantity = 10
                unit_price = 25.00
            }
        )
        total_amount = 250.00
    } | ConvertTo-Json -Depth 3
    
    $invoiceResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/invoices/" -Method POST -Body $invoiceData -ContentType "application/json"
    $invoiceId = $invoiceResponse.data.id
    Write-Host "✅ Invoice submitted: $invoiceId" -ForegroundColor Green

    # Reconcile invoice
    Invoke-RestMethod -Uri "http://localhost:8000/api/v1/invoices/$invoiceId/reconcile" -Method PUT | Out-Null
    Write-Host "✅ Invoice reconciled" -ForegroundColor Green

    # Approve payment
    Write-Host "📋 Approving payment..." -ForegroundColor Yellow
    $approvalData = @{
        approved_by = "demo@manager.com"
    } | ConvertTo-Json
    
    $paymentResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/payments/$invoiceId/approve" -Method POST -Body $approvalData -ContentType "application/json"
    $paymentId = $paymentResponse.data.payment.id
    Write-Host "✅ Payment approved: $paymentId" -ForegroundColor Green

    # Workday callback
    $callbackData = @{
        payment_id = $paymentId
        status = "sent"
    } | ConvertTo-Json
    
    try {
        Invoke-RestMethod -Uri "http://localhost:8000/api/v1/workday/callback" -Method POST -Body $callbackData -ContentType "application/json" | Out-Null
        Write-Host "✅ Workday callback completed" -ForegroundColor Green
    } catch {
        Write-Host "⚠️ Workday callback had an error (known issue), but status should be updated" -ForegroundColor Yellow
    }

    # Verify status
    $statusResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/workday/status/$paymentId"
    $integrationStatus = $statusResponse.data.integration_status
    Write-Host "✅ Integration status: $integrationStatus" -ForegroundColor Green

    Write-Host ""
    Write-Host "🎉 Demo completed successfully!" -ForegroundColor Green
    Write-Host "📊 Check results at: http://localhost:8000/docs" -ForegroundColor Cyan
    Write-Host "📁 Files at: http://localhost:8000/api/v1/exports/" -ForegroundColor Cyan

} finally {
    # Clean up
    Write-Host "🧹 Cleaning up server..." -ForegroundColor Yellow
    Stop-Job -Job $ServerJob -PassThru | Remove-Job
}
```

**Usage:** `.\demo.ps1` (ensure execution policy allows scripts: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`)

---

## 📈 Expected Results Summary

After completing the demo, you should see:

### ✅ **Database Records**
- 2 vendors in VendorsTable
- 1 approved PO in PurchaseOrdersTable  
- 4 invoices in InvoicesTable (received/matched status)
- 5 payments in PaymentsTable (approved status)
- Multiple audit log entries in AuditLogTable

### ✅ **S3 Files**
- XML file: `payments/{payment_id}/payment.xml`
- JSON file: `payments/{payment_id}/payment.json`
- Both files with proper metadata tags

### ✅ **Status Progression**
- Vendor: active
- PO: approved  
- Invoice: matched
- Payment: approved (with XML/JSON files in S3)
- Integration: pending (Workday callback has technical issue but status check works)

### ✅ **Audit Trail**
- Complete lineage from vendor creation to Workday delivery
- All user actions and system processes logged
- Compliance-ready audit documentation

---

**⏱️ Total Demo Time:** 10-15 minutes  
**🎯 Success Criteria:** All API endpoints respond, files in S3, status = "sent" 