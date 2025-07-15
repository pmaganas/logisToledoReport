#!/usr/bin/env python3
"""
Test script to debug the specific SSL issue with a single API call
"""
from services.sesame_api import SesameAPI
import logging

logging.basicConfig(level=logging.DEBUG)

def test_single_break_call():
    """Test a single break API call"""
    api = SesameAPI()
    
    print("Testing single break API call...")
    
    try:
        # Make a single call with no pagination
        result = api.get_breaks(page=1, limit=100)
        
        if result:
            print(f"✓ Success! Got {len(result.get('data', []))} break records")
            print(f"Meta: {result.get('meta', {})}")
        else:
            print("✗ No data returned")
            
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()

def test_single_time_call():
    """Test a single time tracking call"""
    api = SesameAPI()
    
    print("\nTesting single time tracking API call...")
    
    try:
        # Make a single call with no pagination
        result = api.get_work_entries(page=1, limit=20)
        
        if result:
            print(f"✓ Success! Got {len(result.get('data', []))} time records")
            print(f"Meta: {result.get('meta', {})}")
        else:
            print("✗ No data returned")
            
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_single_break_call()
    test_single_time_call()