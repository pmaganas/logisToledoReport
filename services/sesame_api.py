import requests
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class SesameAPI:
    def __init__(self):
        self.token, self.region = self._get_token_and_region()
        self.base_url = f"https://api-{self.region}.sesametime.com"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        self.logger = logging.getLogger(__name__)
    
    def _get_token_and_region(self):
        """Get token and region from database or environment"""
        try:
            from models import SesameToken
            from app import db
            
            # Try to get token from database
            active_token = SesameToken.get_active_token()
            if active_token:
                return active_token.token, active_token.region
        except Exception as e:
            # Logger might not be initialized yet
            print(f"Could not get token from database: {str(e)}")
        
        # Fallback to environment variable
        token = os.getenv("SESAME_TOKEN")
        region = os.getenv("SESAME_REGION", "eu1")
        if not token:
            print("No token configured")
            return None, region
        
        return token, region

    def _make_request(self, endpoint: str, method: str = "GET", params: Dict = None, data: Dict = None) -> Optional[Dict]:
        """Make a request to the Sesame API"""
        url = f"{self.base_url}{endpoint}"
        
        # Create a session with specific configuration to avoid proxy issues
        session = requests.Session()
        session.trust_env = False  # Disable environment proxy settings
        
        # Configure SSL and connection settings
        adapter = requests.adapters.HTTPAdapter(
            max_retries=3,
            pool_connections=10,
            pool_maxsize=10
        )
        session.mount('https://', adapter)
        session.mount('http://', adapter)
        
        try:
            response = session.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                json=data,
                timeout=(30, 60),  # Connection timeout, read timeout
                proxies={},  # Explicitly disable proxies
                verify=True  # Verify SSL certificates
            )
            
            self.logger.debug(f"API Request: {method} {url} - Status: {response.status_code}")
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"API Error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            self.logger.error(f"Request timeout for {url}")
            return None
        except requests.exceptions.SSLError as e:
            self.logger.error(f"SSL error for {url}: {str(e)}")
            return None
        except requests.exceptions.ConnectionError as e:
            self.logger.error(f"Connection error for {url}: {str(e)}")
            return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error for {url}: {str(e)}")
            return None
        finally:
            session.close()

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
            try:
                response = self.get_employees(company_id=company_id, page=page, per_page=100)
                if not response or not response.get("data"):
                    break
                    
                employees = response["data"]
                if isinstance(employees, list):
                    all_employees.extend(employees)
                else:
                    all_employees.append(employees)
                
                self.logger.info(f"Fetched page {page}, total employees: {len(all_employees)}")
                
                # Check if there are more pages
                meta = response.get("meta", {})
                if page >= meta.get("lastPage", 1):
                    break
                    
                page += 1
                
                # Safety check to avoid infinite loops
                if page > 50:  # Max 5000 employees
                    break
                    
            except Exception as e:
                self.logger.error(f"Error fetching employees page {page}: {str(e)}")
                break
                
        return all_employees

    def get_all_time_tracking_data(self, employee_id: str = None, company_id: str = None,
                                  from_date: str = None, to_date: str = None) -> List[Dict]:
        """Get all time tracking data with pagination"""
        all_entries = []
        page = 1
        
        self.logger.info(f"WORK-ENTRIES: Starting fetch for employee {employee_id} from {from_date} to {to_date}")
        
        while True:
            try:
                response = self.get_time_tracking(
                    employee_id=employee_id,
                    company_id=company_id,
                    from_date=from_date,
                    to_date=to_date,
                    page=page,
                    limit=100
                )
                
                self.logger.info(f"WORK-ENTRIES: Requesting page {page}")
                
                if not response:
                    self.logger.info(f"WORK-ENTRIES: No response on page {page}, stopping pagination")
                    break
                    
                if not response.get("data"):
                    self.logger.info(f"WORK-ENTRIES: No data on page {page}, stopping pagination")
                    break
                    
                entries = response["data"]
                if isinstance(entries, list):
                    all_entries.extend(entries)
                    self.logger.info(f"WORK-ENTRIES: Page {page} - got {len(entries)} entries, total so far: {len(all_entries)}")
                else:
                    all_entries.append(entries)
                    self.logger.info(f"WORK-ENTRIES: Page {page} - got 1 entry, total so far: {len(all_entries)}")
                
                # Check if there are more pages
                meta = response.get("meta", {})
                current_page = meta.get("currentPage", page)
                last_page = meta.get("lastPage", 1)
                total_items = meta.get("total", meta.get("totalItems", 0))
                
                self.logger.info(f"WORK-ENTRIES: Page {current_page} of {last_page}, total items: {total_items}")
                
                # Si no hay más entradas en esta página, terminamos
                if len(entries) == 0:
                    self.logger.info(f"WORK-ENTRIES: No entries in page {page}, stopping pagination")
                    break
                    
                if current_page >= last_page:
                    self.logger.info(f"WORK-ENTRIES: Reached last page ({last_page}), stopping pagination")
                    break
                    
                page += 1
                
                # Safety check to avoid infinite loops - increased to handle large datasets
                if page > 200:  # Max 20000 entries
                    self.logger.warning(f"WORK-ENTRIES: Reached safety limit of 200 pages, stopping pagination")
                    break
                    
            except Exception as e:
                self.logger.error(f"Error fetching time tracking data page {page}: {str(e)}")
                break
        
        self.logger.info(f"WORK-ENTRIES: COMPLETED - Fetched {len(all_entries)} total entries across {page-1} pages")
        return all_entries

    def get_all_breaks_data(self, employee_id: str = None, company_id: str = None,
                           from_date: str = None, to_date: str = None) -> List[Dict]:
        """Get all break data with pagination"""
        all_breaks = []
        page = 1
        
        self.logger.info(f"Starting break data fetch for employee {employee_id} from {from_date} to {to_date}")
        
        while True:
            try:
                response = self.get_breaks(
                    employee_id=employee_id,
                    company_id=company_id,
                    from_date=from_date,
                    to_date=to_date,
                    page=page,
                    limit=100
                )
                
                if not response or not response.get("data"):
                    self.logger.info(f"No more break data on page {page}, stopping pagination")
                    break
                    
                breaks = response["data"]
                if isinstance(breaks, list):
                    all_breaks.extend(breaks)
                    self.logger.info(f"Fetched break page {page}, got {len(breaks)} breaks, total so far: {len(all_breaks)}")
                else:
                    all_breaks.append(breaks)
                    self.logger.info(f"Fetched break page {page}, got 1 break, total so far: {len(all_breaks)}")
                
                # Check if there are more pages
                meta = response.get("meta", {})
                current_page = meta.get("currentPage", page)
                last_page = meta.get("lastPage", 1)
                total_items = meta.get("totalItems", 0)
                
                self.logger.info(f"Break page {current_page} of {last_page}, total items: {total_items}")
                
                if page >= last_page:
                    self.logger.info(f"Reached last break page ({last_page}), stopping pagination")
                    break
                    
                page += 1
                
                # Safety check to avoid infinite loops
                if page > 100:
                    self.logger.warning(f"Reached safety limit of 100 break pages, stopping pagination")
                    break
                    
            except Exception as e:
                self.logger.error(f"Error fetching break data page {page}: {str(e)}")
                break
        
        self.logger.info(f"Completed break data fetch: {len(all_breaks)} total breaks")
        return all_breaks

    def get_offices(self, company_id: str = None, page: int = 1, per_page: int = 100) -> Optional[Dict]:
        """Get list of offices/centers"""
        params = {
            "page": page,
            "per_page": per_page
        }
        if company_id:
            params["companyId"] = company_id
            
        return self._make_request("/core/v3/offices", params=params)

    def get_departments(self, company_id: str = None, page: int = 1, per_page: int = 100) -> Optional[Dict]:
        """Get list of departments"""
        params = {
            "page": page,
            "per_page": per_page
        }
        if company_id:
            params["companyId"] = company_id
            
        return self._make_request("/core/v3/departments", params=params)

    def get_all_offices_data(self, company_id: str = None) -> List[Dict]:
        """Get all offices with pagination"""
        all_offices = []
        page = 1
        per_page = 100
        
        while True:
            try:
                response = self.get_offices(company_id=company_id, page=page, per_page=per_page)
                
                if not response or 'data' not in response:
                    break
                
                offices_data = response['data']
                if not offices_data:
                    break
                
                all_offices.extend(offices_data)
                
                # Check if there are more pages
                meta = response.get("meta", {})
                if page >= meta.get("lastPage", 1):
                    break
                
                page += 1
                
            except Exception as e:
                self.logger.error(f"Error getting offices data page {page}: {str(e)}")
                break
        
        return all_offices

    def get_all_departments_data(self, company_id: str = None) -> List[Dict]:
        """Get all departments with pagination"""
        all_departments = []
        page = 1
        per_page = 100
        
        while True:
            try:
                response = self.get_departments(company_id=company_id, page=page, per_page=per_page)
                
                if not response or 'data' not in response:
                    break
                
                departments_data = response['data']
                if not departments_data:
                    break
                
                all_departments.extend(departments_data)
                
                # Check if there are more pages
                meta = response.get("meta", {})
                if page >= meta.get("lastPage", 1):
                    break
                
                page += 1
                
            except Exception as e:
                self.logger.error(f"Error getting departments data page {page}: {str(e)}")
                break
        
        return all_departments

    def get_check_types(self, company_id: str = None, page: int = 1, per_page: int = 100) -> Optional[Dict]:
        """Get list of check types"""
        params = {
            'page': page,
            'per_page': per_page
        }
        
        if company_id:
            params['companyId'] = company_id
        
        return self._make_request("/schedule/v1/check-types", params=params)

    def get_all_check_types_data(self, company_id: str = None) -> List[Dict]:
        """Get all check types with pagination"""
        all_check_types = []
        page = 1
        
        while True:
            try:
                result = self.get_check_types(company_id=company_id, page=page, per_page=100)
                if not result or not result.get('data'):
                    break
                
                all_check_types.extend(result['data'])
                
                # Check if there are more pages
                meta = result.get('meta', {})
                if page >= meta.get('lastPage', 1):
                    break
                
                page += 1
                
            except Exception as e:
                self.logger.error(f"Error getting check types data page {page}: {str(e)}")
                break
        
        return all_check_types
