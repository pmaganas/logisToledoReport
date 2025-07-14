#!/usr/bin/env python3
"""
Test script to debug pagination issues
"""
import sys
sys.path.append('.')

from app import app
from services.sesame_api import SesameAPI
import json

def test_pagination():
    """Test pagination directly"""
    with app.app_context():
        api = SesameAPI()
        
        # Test with a specific date range
        from_date = "2025-07-01"
        to_date = "2025-07-14"
        
        print(f"Testing pagination from {from_date} to {to_date}")
        
        # Test first page
        response = api.get_work_entries(
            from_date=from_date,
            to_date=to_date,
            page=1,
            limit=20
        )
        
        if response:
            print(f"First page response:")
            print(f"- Data entries: {len(response.get('data', []))}")
            print(f"- Meta: {response.get('meta', {})}")
            
            meta = response.get('meta', {})
            total_pages = meta.get('lastPage', 1)
            total_items = meta.get('totalItems', 0)
            
            print(f"- Total pages: {total_pages}")
            print(f"- Total items: {total_items}")
            
            # Test second page
            if total_pages > 1:
                response2 = api.get_work_entries(
                    from_date=from_date,
                    to_date=to_date,
                    page=2,
                    limit=20
                )
                
                if response2:
                    print(f"\nSecond page response:")
                    print(f"- Data entries: {len(response2.get('data', []))}")
                    print(f"- Meta: {response2.get('meta', {})}")
            
            # Test the get_all_time_tracking_data method
            print("\nTesting get_all_time_tracking_data method:")
            all_entries = api.get_all_time_tracking_data(
                from_date=from_date,
                to_date=to_date
            )
            
            print(f"Total entries retrieved: {len(all_entries)}")
            print(f"Expected: {total_items}")
            
            if len(all_entries) != total_items:
                print("ERROR: Mismatch between expected and actual entries!")
            else:
                print("SUCCESS: All entries retrieved correctly")
        else:
            print("ERROR: No response from API")

if __name__ == "__main__":
    test_pagination()