#!/usr/bin/env python3
"""
Simple script to test backend connectivity
"""
import requests
import sys
import time

def test_backend():
    base_url = "http://localhost:8000"
    endpoints = ["/ping", "/health", "/"]
    
    print("🔍 Testing backend connectivity...")
    print(f"🌐 Base URL: {base_url}")
    print("-" * 50)
    
    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        try:
            print(f"Testing {url}...")
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✅ {endpoint}: OK ({response.status_code})")
                data = response.json()
                if endpoint == "/health":
                    print(f"   Status: {data.get('status')}")
                    print(f"   Database: {data.get('services', {}).get('database')}")
            else:
                print(f"❌ {endpoint}: Failed ({response.status_code})")
        except requests.exceptions.ConnectionError:
            print(f"❌ {endpoint}: Connection refused")
        except requests.exceptions.Timeout:
            print(f"❌ {endpoint}: Timeout")
        except Exception as e:
            print(f"❌ {endpoint}: Error - {e}")
    
    print("-" * 50)
    print("🏁 Test complete")

if __name__ == "__main__":
    test_backend()
