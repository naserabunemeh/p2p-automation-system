from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from datetime import datetime, timezone

# Import route modules
from .routes import vendors, purchase_orders, invoices, payments, exports, workday

# Initialize FastAPI app
app = FastAPI(
    title="ERP-Lite P2P Automation System",
    description="Procure-to-Pay automation system with AWS integration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(vendors.router, prefix="/api/v1/vendors", tags=["vendors"])
app.include_router(purchase_orders.router, prefix="/api/v1/purchase-orders", tags=["purchase-orders"])
app.include_router(invoices.router, prefix="/api/v1/invoices", tags=["invoices"])
app.include_router(payments.router, prefix="/api/v1/payments", tags=["payments"])
app.include_router(exports.router, prefix="/api/v1/exports", tags=["exports"])
app.include_router(workday.router, prefix="/api/v1/workday", tags=["workday"])

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and load balancers"""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "P2P Automation System",
            "version": "1.0.0"
        }
    )

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Welcome to ERP-Lite P2P Automation System",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 