import requests
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class SesameAPI:
    def __init__(self):
        self.base_url = "https://api-eu1.sesametime.com"
        self.token = os.getenv("SESAME_TOKEN", "13896c4d68b9c4f92b6243d4616b2c50c605cb2bf8e7c158d8267a676bfd83cb")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        self.logger = logging.getLogger(__name__)

    def _make_request(self, endpoint: str, method: str = "GET", params: Dict = None, data: Dict = None) -> Optional[Dict]:
        """Make a request to the Sesame API"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                json=data,
                timeout=30
            )
            
            self.logger.debug(f"API Request: {method} {url} - Status: {response.status_code}")
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"API Error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {str(e)}")
            return None

    def get_token_info(self) -> Optional[Dict]:
        """Get information about the current token"""
        return self._make_request("/core/v3/info")

    def get_employees(self, company_id: str = None, page: int = 1, per_page: int = 100) -> Optional[Dict]:
        """Get list of employees"""
        params = {
            "page": page,
            "per_page": per_page
        }
        if company_id:
            params["companyId"] = company_id
            
        return self._make_request("/core/v3/employees", params=params)

    def get_employee_details(self, employee_id: str) -> Optional[Dict]:
        """Get details of a specific employee"""
        return self._make_request(f"/core/v3/employees/{employee_id}")

    def get_work_entries(self, employee_id: str = None, company_id: str = None, 
                        from_date: str = None, to_date: str = None, 
                        page: int = 1, limit: int = 100) -> Optional[Dict]:
        """Get work entries (time tracking data)"""
        params = {
            "page": page,
            "limit": limit
        }
        
        if employee_id:
            params["employeeId"] = employee_id
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
            
        return self._make_request("/schedule/v1/work-entries", params=params)

    def get_activities(self, company_id: str = None, page: int = 1, per_page: int = 100) -> Optional[Dict]:
        """Get list of activities"""
        params = {
            "page": page,
            "per_page": per_page
        }
        if company_id:
            params["companyId"] = company_id
            
        return self._make_request("/core/v3/activities", params=params)

    def get_time_tracking(self, employee_id: str = None, company_id: str = None,
                         from_date: str = None, to_date: str = None,
                         page: int = 1, limit: int = 100) -> Optional[Dict]:
        """Get time tracking entries - using work-entries endpoint"""
        return self.get_work_entries(employee_id, company_id, from_date, to_date, page, limit)

    def get_breaks(self, employee_id: str = None, company_id: str = None,
                   from_date: str = None, to_date: str = None,
                   page: int = 1, limit: int = 100) -> Optional[Dict]:
        """Get break entries"""
        params = {
            "page": page,
            "limit": limit
        }
        
        if employee_id:
            params["employeeId"] = employee_id
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
            
        return self._make_request("/schedule/v1/work-breaks", params=params)

    def get_all_employees_data(self, company_id: str = None) -> List[Dict]:
        """Get all employees with pagination"""
        all_employees = []
        page = 1
        
        while True:
            response = self.get_employees(company_id=company_id, page=page, per_page=100)
            if not response or not response.get("data"):
                break
                
            employees = response["data"]
            if isinstance(employees, list):
                all_employees.extend(employees)
            else:
                all_employees.append(employees)
            
            # Check if there are more pages
            meta = response.get("meta", {})
            if page >= meta.get("lastPage", 1):
                break
                
            page += 1
            
        return all_employees

    def get_all_time_tracking_data(self, employee_id: str = None, company_id: str = None,
                                  from_date: str = None, to_date: str = None) -> List[Dict]:
        """Get all time tracking data with pagination"""
        all_entries = []
        page = 1
        
        while True:
            response = self.get_time_tracking(
                employee_id=employee_id,
                company_id=company_id,
                from_date=from_date,
                to_date=to_date,
                page=page,
                limit=100
            )
            
            if not response or not response.get("data"):
                break
                
            entries = response["data"]
            if isinstance(entries, list):
                all_entries.extend(entries)
            else:
                all_entries.append(entries)
            
            # Check if there are more pages
            meta = response.get("meta", {})
            if page >= meta.get("lastPage", 1):
                break
                
            page += 1
            
        return all_entries

    def get_all_breaks_data(self, employee_id: str = None, company_id: str = None,
                           from_date: str = None, to_date: str = None) -> List[Dict]:
        """Get all break data with pagination"""
        all_breaks = []
        page = 1
        
        while True:
            response = self.get_breaks(
                employee_id=employee_id,
                company_id=company_id,
                from_date=from_date,
                to_date=to_date,
                page=page,
                limit=100
            )
            
            if not response or not response.get("data"):
                break
                
            breaks = response["data"]
            if isinstance(breaks, list):
                all_breaks.extend(breaks)
            else:
                all_breaks.append(breaks)
            
            # Check if there are more pages
            meta = response.get("meta", {})
            if page >= meta.get("lastPage", 1):
                break
                
            page += 1
            
        return all_breaks
