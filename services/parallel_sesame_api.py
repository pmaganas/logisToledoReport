import requests
import logging
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from models import SesameToken, db
import time

class ParallelSesameAPI:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.token = None
        self.base_url = None
        self._get_token_and_region()
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        } if self.token else {}
        
        # Create a session with connection pooling
        self.session = requests.Session()
        retry_strategy = requests.adapters.Retry(
            total=2,
            backoff_factor=0.3,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST"])
        adapter = requests.adapters.HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=20,
            pool_maxsize=20,
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
        """Make HTTP request to Sesame API"""
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
                timeout=(5, 15),
                proxies={},
                verify=True
            )

            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(
                    f"API Error: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            self.logger.error(f"Request failed for {url}: {str(e)}")
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
                         limit: int = 500) -> Optional[Dict]:
        """Get work entries (time tracking data)"""
        params: Dict[str, any] = {"page": page, "limit": limit}

        if employee_id:
            params["employeeId"] = employee_id
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        
        params["sort"] = "workEntryIn.date,workEntryIn.createdAt"
        params["order"] = "asc"

        return self._make_request("/schedule/v1/work-entries", params=params)

    def get_time_tracking(self,
                          employee_id: Optional[str] = None,
                          company_id: Optional[str] = None,
                          from_date: Optional[str] = None,
                          to_date: Optional[str] = None,
                          page: int = 1,
                          limit: int = 500) -> Optional[Dict]:
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

    def _fetch_page(self, page: int, employee_id: Optional[str], 
                    company_id: Optional[str], from_date: Optional[str], 
                    to_date: Optional[str], limit: int) -> tuple:
        """Fetch a single page of data"""
        try:
            self.logger.info(f"[PARALLEL] Fetching page {page}...")
            start_time = time.time()
            
            response = self.get_time_tracking(
                employee_id=employee_id,
                company_id=company_id,
                from_date=from_date,
                to_date=to_date,
                page=page,
                limit=limit)
            
            elapsed = time.time() - start_time
            
            if response and response.get("data"):
                data = response["data"]
                meta = response.get("meta", {})
                total = meta.get("total", 0)
                self.logger.info(f"[PARALLEL] Page {page} completed in {elapsed:.1f}s - {len(data)} records")
                return (page, data, total)
            else:
                self.logger.warning(f"[PARALLEL] Page {page} returned no data")
                return (page, [], 0)
                
        except Exception as e:
            self.logger.error(f"[PARALLEL] Error fetching page {page}: {str(e)}")
            return (page, [], 0)

    def get_all_time_tracking_data_parallel(self,
                                           employee_id: Optional[str] = None,
                                           company_id: Optional[str] = None,
                                           from_date: Optional[str] = None,
                                           to_date: Optional[str] = None,
                                           max_pages: int = 100,
                                           max_workers: int = 5) -> List[Dict]:
        """Get all time tracking data with parallel pagination"""
        all_data = []
        limit = 500
        
        # First, get page 1 to determine total pages
        self.logger.info("[PARALLEL] Getting first page to determine total...")
        first_response = self.get_time_tracking(
            employee_id=employee_id,
            company_id=company_id,
            from_date=from_date,
            to_date=to_date,
            page=1,
            limit=limit)
        
        if not first_response or not first_response.get("data"):
            self.logger.error("[PARALLEL] Failed to get first page")
            return []
        
        all_data.extend(first_response["data"])
        meta = first_response.get("meta", {})
        total_pages = min(meta.get("lastPage", 1), max_pages)
        total_records = meta.get("total", 0)
        
        self.logger.info(f"[PARALLEL] Total pages: {total_pages}, Total records: {total_records}")
        
        if total_pages <= 1:
            return all_data
        
        # Fetch remaining pages in parallel
        pages_to_fetch = list(range(2, total_pages + 1))
        self.logger.info(f"[PARALLEL] Starting parallel fetch of {len(pages_to_fetch)} pages with {max_workers} workers...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_page = {
                executor.submit(self._fetch_page, page, employee_id, 
                               company_id, from_date, to_date, limit): page 
                for page in pages_to_fetch
            }
            
            # Process completed tasks
            completed = 0
            for future in as_completed(future_to_page):
                page_num, data, _ = future.result()
                if data:
                    all_data.extend(data)
                completed += 1
                
                if completed % 10 == 0:
                    self.logger.info(f"[PARALLEL] Progress: {completed}/{len(pages_to_fetch)} pages completed")
        
        # Sort all data by date and time
        all_data.sort(key=lambda x: (
            x.get('workEntryIn', {}).get('date', ''),
            x.get('workEntryIn', {}).get('time', '')
        ))
        
        self.logger.info(f"[PARALLEL] Total records retrieved: {len(all_data)}")
        return all_data

    def get_all_time_tracking_data(self,
                                   employee_id: Optional[str] = None,
                                   company_id: Optional[str] = None,
                                   from_date: Optional[str] = None,
                                   to_date: Optional[str] = None,
                                   max_pages: int = 100) -> List[Dict]:
        """Get all time tracking data - use parallel version for better performance"""
        return self.get_all_time_tracking_data_parallel(
            employee_id=employee_id,
            company_id=company_id,
            from_date=from_date,
            to_date=to_date,
            max_pages=max_pages,
            max_workers=5  # Adjust based on API rate limits
        )