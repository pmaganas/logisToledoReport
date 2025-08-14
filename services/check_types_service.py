import logging
from typing import Dict, List, Optional
from services.sesame_api import SesameAPI
from models import CheckType
from app import db

logger = logging.getLogger(__name__)


class CheckTypesService:
    """Service to manage check types (activity types) caching"""
    
    def __init__(self):
        self.api = SesameAPI()
        # Cache for activity names to avoid repeated DB queries
        self._activity_cache = {}
    
    def sync_check_types(self) -> bool:
        """Sync all check types from API to database"""
        try:
            # Get all check types from API using pagination
            check_types = self._get_all_check_types()
            
            if not check_types:
                logger.error("No check types retrieved from API")
                return False
            
            # Bulk upsert to database
            CheckType.bulk_upsert(check_types)
            
            # Clear cache after sync to force reload
            self._activity_cache.clear()
            
            logger.info(f"Synchronized {len(check_types)} check types to database")
            return True
            
        except Exception as e:
            logger.error(f"Error synchronizing check types: {str(e)}")
            return False
    
    def _get_all_check_types(self) -> List[Dict]:
        """Get all check types from API with pagination"""
        all_check_types = []
        page = 1
        
        while True:
            try:
                response = self.api.get_check_types(page=page, limit=100)
                
                if not response or 'data' not in response:
                    break
                
                check_types = response['data']
                
                if not check_types:
                    break
                
                # Process each check type
                for check_type in check_types:
                    processed_type = {
                        'id': check_type.get('id', ''),
                        'name': check_type.get('name', ''),
                        'description': check_type.get('description', '')
                    }
                    all_check_types.append(processed_type)
                
                # Check if there are more pages
                metadata = response.get('metadata', {})
                total_pages = metadata.get('totalPages', 1)
                
                if page >= total_pages:
                    break
                
                page += 1
                
            except Exception as e:
                logger.error(f"Error getting check types page {page}: {str(e)}")
                break
        
        return all_check_types
    
    def get_activity_name(self, work_entry_type: str, work_break_id: Optional[str]) -> str:
        """Get activity name based on work entry type and break ID - with caching"""
        try:
            # Create cache key
            cache_key = f"{work_entry_type}_{work_break_id or 'None'}"
            
            # Check cache first
            if cache_key in self._activity_cache:
                return self._activity_cache[cache_key]
            
            # If workEntryType is 'work' and workBreakId is null, it's normal work
            if work_entry_type == 'work' and not work_break_id:
                result = 'Registro normal'
            # If workBreakId has a value, look up the check type name
            elif work_break_id:
                result = CheckType.get_name_by_id(work_break_id)
            else:
                # Default fallback
                result = work_entry_type or 'Actividad desconocida'
            
            # Cache the result
            self._activity_cache[cache_key] = result
            return result
            
        except Exception as e:
            logger.error(f"Error getting activity name: {str(e)}")
            return 'Actividad desconocida'
    
    def ensure_check_types_cached(self) -> bool:
        """Ensure check types are cached in database"""
        try:
            # Check if we have any check types in database
            check_types_count = CheckType.query.count()
            
            if check_types_count == 0:
                logger.info("No check types in cache, syncing from API...")
                return self.sync_check_types()
            
            logger.info(f"Check types cache ready: {check_types_count} types available")
            return True
            
        except Exception as e:
            logger.error(f"Error checking cached check types: {str(e)}")
            return False
    
    def refresh_check_types(self) -> bool:
        """Force refresh of check types from API"""
        try:
            # Delete all existing check types
            CheckType.query.delete()
            db.session.commit()
            
            # Clear cache
            self._activity_cache.clear()
            
            # Sync from API
            return self.sync_check_types()
            
        except Exception as e:
            logger.error(f"Error refreshing check types: {str(e)}")
            return False
    
    def warm_up_cache(self, entries: List[Dict]) -> None:
        """Pre-warm the activity cache with all unique combinations from entries"""
        try:
            unique_combinations = set()
            for entry in entries:
                work_entry_type = entry.get('workEntryType', '')
                work_break_id = entry.get('workBreakId')
                unique_combinations.add((work_entry_type, work_break_id))
            
            logger.info(f"Warming up activity cache with {len(unique_combinations)} unique combinations...")
            
            for work_entry_type, work_break_id in unique_combinations:
                self.get_activity_name(work_entry_type, work_break_id)
                
            logger.info(f"Activity cache warmed up with {len(self._activity_cache)} cached entries")
            
        except Exception as e:
            logger.error(f"Error warming up cache: {str(e)}")