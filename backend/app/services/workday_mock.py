from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import uuid
import json
import random

class WorkdayMockService:
    """Mock service to simulate Workday API interactions"""
    
    def __init__(self):
        self.mock_data = {
            "vendors": {},
            "employees": {},
            "cost_centers": {},
            "gl_accounts": {}
        }
        self._initialize_mock_data()
    
    def _initialize_mock_data(self):
        """Initialize mock data for testing"""
        # Mock employees
        self.mock_data["employees"] = {
            "EMP001": {
                "id": "EMP001",
                "name": "John Smith",
                "email": "john.smith@company.com",
                "department": "Finance",
                "manager_id": "EMP002",
                "cost_center": "CC001"
            },
            "EMP002": {
                "id": "EMP002",
                "name": "Sarah Johnson",
                "email": "sarah.johnson@company.com",
                "department": "Finance",
                "manager_id": None,
                "cost_center": "CC001"
            },
            "EMP003": {
                "id": "EMP003",
                "name": "Mike Davis",
                "email": "mike.davis@company.com",
                "department": "IT",
                "manager_id": "EMP004",
                "cost_center": "CC002"
            }
        }
        
        # Mock cost centers
        self.mock_data["cost_centers"] = {
            "CC001": {
                "id": "CC001",
                "name": "Finance Department",
                "budget": 500000.00,
                "manager": "EMP002"
            },
            "CC002": {
                "id": "CC002",
                "name": "IT Department",
                "budget": 750000.00,
                "manager": "EMP004"
            }
        }
        
        # Mock GL accounts
        self.mock_data["gl_accounts"] = {
            "GL001": {
                "id": "GL001",
                "name": "Office Supplies",
                "account_type": "Expense",
                "category": "Operating Expenses"
            },
            "GL002": {
                "id": "GL002",
                "name": "Software Licenses",
                "account_type": "Expense",
                "category": "IT Expenses"
            },
            "GL003": {
                "id": "GL003",
                "name": "Accounts Payable",
                "account_type": "Liability",
                "category": "Current Liabilities"
            }
        }
    
    def validate_vendor(self, vendor_id: str) -> Dict[str, Any]:
        """
        Mock Workday vendor validation
        
        Args:
            vendor_id: Vendor ID to validate
            
        Returns:
            Validation response
        """
        # Simulate API call delay
        import time
        time.sleep(0.1)
        
        # Mock validation logic
        is_valid = random.choice([True, True, True, False])  # 75% success rate
        
        if is_valid:
            return {
                "success": True,
                "vendor_id": vendor_id,
                "status": "ACTIVE",
                "payment_terms": "Net 30",
                "tax_status": "VERIFIED",
                "bank_account_verified": True,
                "risk_score": random.randint(1, 10),
                "last_updated": datetime.utcnow().isoformat()
            }
        else:
            return {
                "success": False,
                "vendor_id": vendor_id,
                "errors": ["Vendor not found in Workday", "Invalid tax ID"],
                "status": "INACTIVE"
            }
    
    def get_employee_info(self, employee_id: str) -> Optional[Dict[str, Any]]:
        """
        Mock Workday employee lookup
        
        Args:
            employee_id: Employee ID to lookup
            
        Returns:
            Employee information or None
        """
        return self.mock_data["employees"].get(employee_id)
    
    def validate_approval_hierarchy(self, employee_id: str, amount: float) -> Dict[str, Any]:
        """
        Mock approval hierarchy validation
        
        Args:
            employee_id: Employee requesting approval
            amount: Amount requiring approval
            
        Returns:
            Approval requirements
        """
        employee = self.get_employee_info(employee_id)
        if not employee:
            return {
                "success": False,
                "error": "Employee not found"
            }
        
        # Mock approval limits
        approval_limits = {
            "EMP001": 5000.00,   # John Smith
            "EMP002": 25000.00,  # Sarah Johnson (Manager)
            "EMP003": 1000.00,   # Mike Davis
            "EMP004": 15000.00   # IT Manager
        }
        
        employee_limit = approval_limits.get(employee_id, 500.00)
        
        if amount <= employee_limit:
            return {
                "success": True,
                "requires_approval": False,
                "approver": employee_id,
                "approval_level": 1
            }
        else:
            # Find manager for approval
            manager_id = employee.get("manager_id")
            if manager_id:
                return {
                    "success": True,
                    "requires_approval": True,
                    "approver": manager_id,
                    "approval_level": 2,
                    "manager_info": self.get_employee_info(manager_id)
                }
            else:
                return {
                    "success": True,
                    "requires_approval": True,
                    "approver": "FINANCE_DIRECTOR",
                    "approval_level": 3,
                    "reason": "Amount exceeds manager authority"
                }
    
    def submit_payment_request(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mock Workday payment submission
        
        Args:
            payment_data: Payment request data
            
        Returns:
            Submission response
        """
        # Simulate processing time
        import time
        time.sleep(0.2)
        
        # Mock submission logic
        success_rate = 0.9  # 90% success rate
        is_successful = random.random() < success_rate
        
        if is_successful:
            workday_payment_id = f"WD-PAY-{str(uuid.uuid4())[:8].upper()}"
            return {
                "success": True,
                "workday_payment_id": workday_payment_id,
                "status": "SUBMITTED",
                "estimated_processing_time": "2-3 business days",
                "tracking_number": f"TRK-{workday_payment_id}",
                "submission_timestamp": datetime.utcnow().isoformat()
            }
        else:
            errors = random.choice([
                ["Invalid vendor bank account"],
                ["Insufficient funds in cost center"],
                ["Payment amount exceeds daily limit"],
                ["Duplicate payment detected"]
            ])
            return {
                "success": False,
                "errors": errors,
                "status": "REJECTED"
            }
    
    def get_payment_status(self, workday_payment_id: str) -> Dict[str, Any]:
        """
        Mock payment status lookup
        
        Args:
            workday_payment_id: Workday payment ID
            
        Returns:
            Payment status information
        """
        # Mock status progression
        statuses = ["SUBMITTED", "PROCESSING", "APPROVED", "SENT_TO_BANK", "COMPLETED"]
        current_status = random.choice(statuses)
        
        status_info = {
            "workday_payment_id": workday_payment_id,
            "status": current_status,
            "last_updated": datetime.utcnow().isoformat()
        }
        
        if current_status == "COMPLETED":
            status_info.update({
                "completion_date": (datetime.utcnow() - timedelta(days=1)).isoformat(),
                "bank_reference": f"BANK-{str(uuid.uuid4())[:8].upper()}",
                "settlement_date": datetime.utcnow().isoformat()
            })
        elif current_status == "PROCESSING":
            status_info["estimated_completion"] = (datetime.utcnow() + timedelta(days=2)).isoformat()
        
        return status_info
    
    def validate_cost_center(self, cost_center_id: str, amount: float) -> Dict[str, Any]:
        """
        Mock cost center validation
        
        Args:
            cost_center_id: Cost center ID
            amount: Amount to validate against budget
            
        Returns:
            Validation response
        """
        cost_center = self.mock_data["cost_centers"].get(cost_center_id)
        
        if not cost_center:
            return {
                "success": False,
                "error": "Cost center not found"
            }
        
        # Mock budget checking
        budget = cost_center["budget"]
        used_budget = random.uniform(0.3, 0.8) * budget  # Random usage between 30-80%
        available_budget = budget - used_budget
        
        return {
            "success": True,
            "cost_center_id": cost_center_id,
            "cost_center_name": cost_center["name"],
            "budget": budget,
            "used_budget": used_budget,
            "available_budget": available_budget,
            "sufficient_funds": available_budget >= amount,
            "manager": cost_center["manager"]
        }
    
    def get_gl_account_info(self, gl_account_id: str) -> Optional[Dict[str, Any]]:
        """
        Mock GL account lookup
        
        Args:
            gl_account_id: GL account ID
            
        Returns:
            GL account information
        """
        return self.mock_data["gl_accounts"].get(gl_account_id)
    
    def generate_workday_report(self, report_type: str, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Mock Workday report generation
        
        Args:
            report_type: Type of report to generate
            filters: Report filters
            
        Returns:
            Report data
        """
        if filters is None:
            filters = {}
        
        # Mock report data based on type
        if report_type == "vendor_payments":
            return {
                "report_type": "vendor_payments",
                "generated_at": datetime.utcnow().isoformat(),
                "total_payments": random.randint(50, 200),
                "total_amount": random.uniform(100000, 500000),
                "status_summary": {
                    "completed": random.randint(40, 80),
                    "processing": random.randint(5, 15),
                    "pending": random.randint(2, 10),
                    "failed": random.randint(0, 3)
                }
            }
        elif report_type == "cost_center_spending":
            return {
                "report_type": "cost_center_spending",
                "generated_at": datetime.utcnow().isoformat(),
                "cost_centers": [
                    {
                        "id": cc_id,
                        "name": cc_data["name"],
                        "budget": cc_data["budget"],
                        "spent": random.uniform(0.3, 0.8) * cc_data["budget"],
                        "remaining": cc_data["budget"] - (random.uniform(0.3, 0.8) * cc_data["budget"])
                    }
                    for cc_id, cc_data in self.mock_data["cost_centers"].items()
                ]
            }
        else:
            return {
                "error": f"Unknown report type: {report_type}",
                "available_reports": ["vendor_payments", "cost_center_spending"]
            } 