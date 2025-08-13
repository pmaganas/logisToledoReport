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
        
        # Create a persistent session for better performance
        self.session = requests.Session()
        retry_strategy = requests.adapters.Retry(
            total=2,
            backoff_factor=0.3,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST"])
        adapter = requests.adapters.HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=10,
            pool_block=False
        )
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)

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
        """Make HTTP request to Sesame API with persistent session"""
        if not self.token or not self.base_url:
            self.logger.error("No token or base URL configured")
            return None

        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                json=data,
                timeout=(5, 15),  # Increased timeouts for better reliability
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
    
    def get_check_type_collections(self, limit: int = 100, page: int = 1) -> Optional[Dict]:
        """Get all check type collections (groups)"""
        params = {
            "limit": limit,
            "page": page
        }
        return self._make_request("/schedule/v1/check-type-collections", params=params)
    
    def get_check_type_collection_details(self, collection_id: str) -> Optional[Dict]:
        """Get details of a specific check type collection including its check types"""
        return self._make_request(f"/schedule/v1/check-type-collections/{collection_id}")
    
    def get_all_check_type_collections_mapping(self) -> Dict[str, str]:
        """Get mapping of check type ID to collection name"""
        mapping = {}
        
        try:
            # First get all collections
            collections_response = self.get_check_type_collections(limit=100)
            if not collections_response or not collections_response.get("data"):
                self.logger.warning("No check type collections found")
                return mapping
            
            collections = collections_response["data"]
            self.logger.info(f"Found {len(collections)} check type collections")
            
            # For each collection, get its check types
            for collection in collections:
                collection_id = collection.get("id")
                collection_name = collection.get("name", "Sin Grupo")
                
                if not collection_id:
                    continue
                
                # Get collection details with check types
                details_response = self.get_check_type_collection_details(collection_id)
                if details_response and details_response.get("data"):
                    # The response is an array with one item
                    collection_data = details_response["data"][0] if isinstance(details_response["data"], list) else details_response["data"]
                    check_types = collection_data.get("checkTypes", [])
                    
                    # Map each check type ID to the collection name
                    for check_type in check_types:
                        check_type_id = check_type.get("id")
                        if check_type_id:
                            mapping[check_type_id] = collection_name
                            self.logger.debug(f"Mapped check type {check_type_id} to collection {collection_name}")
            
            self.logger.info(f"Created mapping for {len(mapping)} check types")
            return mapping
            
        except Exception as e:
            self.logger.error(f"Error creating check type collections mapping: {str(e)}")
            return mapping