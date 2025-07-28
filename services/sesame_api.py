import requests
import logging
from typing import Dict, List, Optional
from models import SesameToken, db

class SesameAPI:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.token = None
        self.base_url = None
        self._get_token_and_region()
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        } if self.token else {}

    def _get_token_and_region(self):
        """Load token and region from database"""
        try:
            token_record = db.session.query(SesameToken).first()
            if token_record:
                self.token = token_record.token
                self.base_url = f"https://api-{token_record.region}.sesametime.com"
            else:
                self.logger.warning("No Sesame token found in database")
                self.token = None
                self.base_url = None
        except Exception as e:
            self.logger.error(f"Error loading token from database: {str(e)}")
            self.token = None
            self.base_url = None

    def _make_request(self,
                      endpoint: str,
                      method: str = "GET",
                      params: Optional[Dict] = None,
                      data: Optional[Dict] = None) -> Optional[Dict]:
        """Make HTTP request to Sesame API with ultra-safe SSL handling"""
        if not self.token or not self.base_url:
            self.logger.error("No token or base URL configured")
            return None

        url = f"{self.base_url}{endpoint}"

        # Create a new session for each request with custom configuration
        session = requests.Session()
        
        # Configure retry strategy with minimal retries
        retry_strategy = requests.adapters.Retry(
            total=2,
            backoff_factor=0.1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST"])
        adapter = requests.adapters.HTTPAdapter(max_retries=retry_strategy,
                                                pool_connections=5,
                                                pool_maxsize=5)
        session.mount('https://', adapter)
        session.mount('http://', adapter)

        try:
            response = session.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                json=data,
                timeout=(2, 5),  # Ultra-reduced timeouts to prevent SSL hangs
                proxies={},  # Explicitly disable proxies
                verify=True  # Verify SSL certificates
            )

            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(
                    f"API Error: {response.status_code} - {response.text}")
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

    def get_work_entries(self,
                         employee_id: Optional[str] = None,
                         company_id: Optional[str] = None,
                         from_date: Optional[str] = None,
                         to_date: Optional[str] = None,
                         page: int = 1,
                         limit: int = 300) -> Optional[Dict]:
        """Get work entries (time tracking data)"""
        params: Dict[str, any] = {"page": page, "limit": limit}

        if employee_id:
            params["employeeId"] = employee_id
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        
        # Add sorting by date and entry time for consistent ordering
        params["sort"] = "workEntryIn.date,workEntryIn.createdAt"
        params["order"] = "asc"

        return self._make_request("/schedule/v1/work-entries", params=params)

    def get_time_tracking(self,
                          employee_id: Optional[str] = None,
                          company_id: Optional[str] = None,
                          from_date: Optional[str] = None,
                          to_date: Optional[str] = None,
                          page: int = 1,
                          limit: int = 300) -> Optional[Dict]:
        """Get time tracking entries - using work-entries endpoint"""
        return self.get_work_entries(employee_id, company_id, from_date,
                                     to_date, page, limit)

    def get_check_types(self,
                       page: int = 1,
                       limit: int = 100) -> Optional[Dict]:
        """Get check types (activity types) for work entries"""
        params = {"page": page, "limit": limit}
        return self._make_request("/schedule/v1/check-types", params=params)

    def get_offices(self) -> Optional[Dict]:
        """Get list of offices"""
        if not self.token:
            self.logger.error("No token configured for offices request")
            return None
            
        try:
            response = self._make_request('/core/v3/offices')
            return response
        except Exception as e:
            self.logger.error(f"Error fetching offices: {str(e)}")
            return None

    def get_departments(self) -> Optional[Dict]:
        """Get list of departments"""
        if not self.token:
            self.logger.error("No token configured for departments request")
            return None
            
        try:
            response = self._make_request('/core/v3/departments')
            return response
        except Exception as e:
            self.logger.error(f"Error fetching departments: {str(e)}")
            return None

    def get_all_time_tracking_data(self,
                                   employee_id: Optional[str] = None,
                                   company_id: Optional[str] = None,
                                   from_date: Optional[str] = None,
                                   to_date: Optional[str] = None,
                                   max_pages: int = 100) -> List[Dict]:
        """Get all time tracking data with pagination"""
        all_data = []
        page = 1
        limit = 300  # Increased from 100 to 300 for performance

        while page <= max_pages:
            try:
                response = self.get_time_tracking(
                    employee_id=employee_id,
                    company_id=company_id,
                    from_date=from_date,
                    to_date=to_date,
                    page=page,
                    limit=limit)

                if not response or not response.get("data"):
                    break

                data = response["data"]
                all_data.extend(data)

                # Check pagination info
                meta = response.get("meta", {})
                total_pages = meta.get("lastPage", 1)
                current_page = meta.get("currentPage", page)

                self.logger.info(
                    f"Page {current_page}/{total_pages} - Retrieved {len(data)} records"
                )

                # Check if we've reached the last page
                if current_page >= total_pages:
                    break

                # If we got less than the limit, we're probably at the end
                if len(data) < limit:
                    break

                page += 1

            except Exception as e:
                self.logger.error(
                    f"Error getting time tracking page {page}: {str(e)}")
                # If we have some data, return what we have
                if all_data:
                    self.logger.warning(
                        f"Returning partial data: {len(all_data)} records")
                    break
                else:
                    # If first page fails, raise the error
                    raise

        self.logger.info(
            f"Total time tracking records retrieved: {len(all_data)}")
        return all_data