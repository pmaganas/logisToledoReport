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
        """Get activity name based on work entry type and break ID"""
        try:
            # If workEntryType is 'work' and workBreakId is null, it's normal work
            if work_entry_type == 'work' and not work_break_id:
                return 'Registro normal'
            
            # If workBreakId has a value, look up the check type name
            if work_break_id:
                return CheckType.get_name_by_id(work_break_id)
            
            # Default fallback
            return work_entry_type or 'Actividad desconocida'
            
        except Exception as e:
            logger.error(f"Error getting activity name: {str(e)}")
            return 'Actividad desconocida'
    
    def ensure_check_types_cached(self) -> bool:
        """Ensure check types are cached in database"""
        try:
            # Check if we have any check types in database
            check_types_count = CheckType.query.count()
            
            if check_types_count == 0:
                return self.sync_check_types()
            
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
            
            # Sync from API
            return self.sync_check_types()
            
        except Exception as e:
            logger.error(f"Error refreshing check types: {str(e)}")
            return False