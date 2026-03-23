"""
Simple test script to verify API endpoints are working.

Usage:
    python test_api.py
"""

import requests
import json
from typing import Dict, Any

BASE_URL = "http://127.0.0.1:8000"
API_V1 = f"{BASE_URL}/api/v1"


def print_response(title: str, response: requests.Response):
    """Pretty print API response"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        try:
            data = response.json()
            if isinstance(data, list):
                print(f"Results: {len(data)} items")
                if data:
                    print(f"Sample: {json.dumps(data[0], indent=2, default=str)[:500]}...")
            else:
                print(json.dumps(data, indent=2, default=str)[:1000])
        except:
            print(response.text[:500])
    else:
        print(response.text[:500])


def test_api():
    """Test all API endpoints"""
    print("\nStarting API tests...")
    print(f"Target: {BASE_URL}")

    # 1. Health check
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print_response("1. Health Check", response)
    except requests.ConnectionError:
        print("\n" + "="*60)
        print("  ERROR: Cannot connect to API")
        print("="*60)
        print(f"Make sure backend is running: uvicorn main:app --reload")
        return

    # 2. Get sources
    try:
        response = requests.get(f"{API_V1}/sources", timeout=5)
        print_response("2. Get Sources", response)
    except Exception as e:
        print(f"Error: {e}")

    # 3. Get statistics
    try:
        response = requests.get(f"{API_V1}/stats", timeout=5)
        print_response("3. Get Statistics", response)
    except Exception as e:
        print(f"Error: {e}")

    # 4. Get opportunities
    try:
        response = requests.get(f"{API_V1}/opportunities?limit=10", timeout=5)
        print_response("4. Get Opportunities (first 10)", response)
    except Exception as e:
        print(f"Error: {e}")

    # 5. Filter by source
    try:
        response = requests.get(f"{API_V1}/opportunities?source=EU Funding & Tenders Portal&limit=5", timeout=5)
        print_response("5. Filter by Source (EU)", response)
    except Exception as e:
        print(f"Error: {e}")

    # 6. Search
    try:
        response = requests.get(f"{API_V1}/opportunities?search=technology&limit=5", timeout=5)
        print_response("6. Search (technology)", response)
    except Exception as e:
        print(f"Error: {e}")

    print("\n" + "="*60)
    print("  Test Summary")
    print("="*60)
    print("If all tests passed (HTTP 200), the API is working correctly.")
    print("\nNext steps:")
    print("  1. Open browser: http://localhost:5173")
    print("  2. Or run: python run_scrapers.py")
    print("  3. Or check API docs: http://127.0.0.1:8000/docs")


if __name__ == "__main__":
    test_api()
