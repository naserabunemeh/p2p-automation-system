# ERP-Lite Procure-to-Pay (P2P) Automation System

## Overview

This is a modern ERP-Lite Procure-to-Pay automation system built with FastAPI and AWS services. The system simulates a complete finance workflow from vendor management through payment processing, with XML-based payment outputs and future Workday API integration.

## Features

- **Vendor Management**: Create, update, and manage vendor information
- **Purchase Order Processing**: Generate and track purchase orders
- **Invoice Management**: Process and approve invoices
- **Payment Automation**: Generate XML and JSON payment records
- **AWS Integration**: DynamoDB for data storage, S3 for file management
- **API Documentation**: Auto-generated OpenAPI/Swagger docs

## Architecture

- **Backend**: FastAPI with async support
- **Database**: AWS DynamoDB
- **Storage**: AWS S3
- **Payment Output**: XML and JSON formats
- **Future Integration**: Workday-style APIs

## Quick Start

### Prerequisites

- Python 3.9+
- AWS CLI configured
- AWS account with DynamoDB and S3 access

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd p2p-automation-system
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
cd backend
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your AWS credentials and configuration
```

5. Initialize AWS resources:
```bash
python ../infra/init_dynamodb.py
python ../infra/init_s3.py
```

6. Run the application:
```bash
python app/main.py
```

The API will be available at `http://localhost:8000`

## API Documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health Check: `http://localhost:8000/health`

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── models.py            # Pydantic data models
│   ├── routes/              # API route handlers
│   │   ├── vendors.py
│   │   ├── purchase_orders.py
│   │   ├── invoices.py
│   │   └── payments.py
│   └── services/            # Business logic services
│       ├── xml_generator.py
│       └── workday_mock.py
├── requirements.txt         # Python dependencies
└── README.md               # This file

infra/
├── aws_resources.md        # AWS architecture documentation
├── init_dynamodb.py       # DynamoDB table initialization
└── init_s3.py            # S3 bucket setup
```

## Environment Variables

Create a `.env` file in the backend directory:

```env
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=YOUR_AWS_ACCESS_KEY_HERE
AWS_SECRET_ACCESS_KEY=YOUR_AWS_SECRET_KEY_HERE
DYNAMODB_TABLE_PREFIX=p2p_
S3_BUCKET_NAME=p2p-automation-bucket
ENVIRONMENT=development
```

## API Endpoints

### Vendors
- `GET /api/v1/vendors` - List all vendors
- `POST /api/v1/vendors` - Create new vendor
- `GET /api/v1/vendors/{id}` - Get vendor by ID
- `PUT /api/v1/vendors/{id}` - Update vendor
- `DELETE /api/v1/vendors/{id}` - Delete vendor

### Purchase Orders
- `GET /api/v1/purchase-orders` - List all purchase orders
- `POST /api/v1/purchase-orders` - Create new purchase order
- `GET /api/v1/purchase-orders/{id}` - Get purchase order by ID
- `PUT /api/v1/purchase-orders/{id}` - Update purchase order
- `DELETE /api/v1/purchase-orders/{id}` - Delete purchase order

### Invoices
- `GET /api/v1/invoices` - List all invoices
- `POST /api/v1/invoices` - Create new invoice
- `GET /api/v1/invoices/{id}` - Get invoice by ID
- `PUT /api/v1/invoices/{id}` - Update invoice
- `DELETE /api/v1/invoices/{id}` - Delete invoice

### Payments
- `GET /api/v1/payments` - List all payments
- `POST /api/v1/payments` - Create new payment
- `GET /api/v1/payments/{id}` - Get payment by ID
- `PUT /api/v1/payments/{id}` - Update payment
- `GET /api/v1/payments/{id}/xml` - Generate XML payment file
- `GET /api/v1/payments/{id}/json` - Generate JSON payment file

## Development

### Running Tests

```bash
pytest
```

### Code Style

This project follows PEP 8 guidelines. Use `black` for code formatting:

```bash
pip install black
black .
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 