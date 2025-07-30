"""
ERP-Lite Procure-to-Pay (P2P) Automation System - Main Application

This module serves as the entry point for the FastAPI-based P2P automation system.
It configures the web application, middleware, routing, and provides core endpoints
for health monitoring and API information.

Features:
    - FastAPI application with automatic OpenAPI documentation
    - CORS middleware for cross-origin requests
    - Modular routing structure for scalability
    - Health check endpoints for monitoring
    - Production-ready configuration options

Author: Development Team
Version: 1.0.0
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from datetime import datetime, timezone

# Import route modules for API endpoints
from .routes import vendors, purchase_orders, invoices, payments, exports, workday

# Initialize FastAPI application with comprehensive metadata
app = FastAPI(
    title="ERP-Lite P2P Automation System",
    description="Procure-to-Pay automation system with AWS integration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure Cross-Origin Resource Sharing (CORS) middleware
# Note: In production, configure origins more restrictively
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production environment
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Register API route modules with appropriate prefixes and tags
# Each module handles a specific domain of the P2P process
app.include_router(vendors.router, prefix="/api/v1/vendors", tags=["vendors"])
app.include_router(purchase_orders.router, prefix="/api/v1/purchase-orders", tags=["purchase-orders"])
app.include_router(invoices.router, prefix="/api/v1/invoices", tags=["invoices"])
app.include_router(payments.router, prefix="/api/v1/payments", tags=["payments"])
app.include_router(exports.router, prefix="/api/v1/exports", tags=["exports"])
app.include_router(workday.router, prefix="/api/v1/workday", tags=["workday"])

# Health check endpoint for monitoring and load balancers
@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.
    
    This endpoint provides a simple way to verify that the application
    is running and responding to requests. It returns current status,
    timestamp, and service information.
    
    Returns:
        JSONResponse: Health status with metadata including:
            - status: Current health status
            - timestamp: Current UTC timestamp
            - service: Service name identifier
            - version: Application version
    """
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "P2P Automation System",
            "version": "1.0.0"
        }
    )

# Root endpoint providing API navigation information
@app.get("/")
async def root():
    """
    Root endpoint with API information and navigation links.
    
    This endpoint serves as the main entry point for API consumers,
    providing basic information about the service and links to
    important resources like documentation and health checks.
    
    Returns:
        dict: API information including:
            - message: Welcome message
            - version: Current API version
            - docs: Link to Swagger documentation
            - health: Link to health check endpoint
    """
    return {
        "message": "Welcome to ERP-Lite P2P Automation System",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

# Application entry point for direct execution
if __name__ == "__main__":
    # Configure uvicorn server with development-friendly settings
    uvicorn.run(
        "main:app",
        host="0.0.0.0",        # Listen on all interfaces
        port=8000,             # Default port for development
        reload=True,           # Auto-reload on code changes
        log_level="info"       # Detailed logging for development
    ) 