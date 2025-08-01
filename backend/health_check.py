#!/usr/bin/env python3
"""
Backend health check script
"""
import requests
import sys
import time
import json

def check_backend():
    """Check if backend is running and accessible"""
    base_url = "http://localhost:8000"
    
    print("🏥 Backend Health Check")
    print("=" * 50)
    print(f"Testing: {base_url}")
    print()
    
    # Test endpoints
    endpoints = [
        ("/ping", "Simple connectivity test"),
        ("/health", "Detailed health check"),
        ("/", "Root endpoint"),
        ("/test", "Test endpoint")
    ]
    
    results = []
    
    for endpoint, description in endpoints:
        url = f"{base_url}{endpoint}"
        try:
            print(f"Testing {endpoint}... ", end="")
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                print(f" OK ({response.status_code})")
                try:
                    data = response.json()
                    if endpoint == "/health":
                        print(f"   Status: {data.get('status', 'unknown')}")
                        services = data.get('services', {})
                        print(f"   Database: {services.get('database', 'unknown')}")
                        print(f"   AI: {services.get('ai', 'unknown')}")
                except:
                    print("   (Non-JSON response)")
                results.append(True)
            else:
                print(f"❌ Failed ({response.status_code})")
                results.append(False)
                
        except requests.exceptions.ConnectionError:
            print("❌ Connection refused")
            results.append(False)
        except requests.exceptions.Timeout:
            print("❌ Timeout")
            results.append(False)
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append(False)
    
    print()
    print("=" * 50)
    
    if any(results):
        print("✅ Backend is partially or fully accessible")
        return True
    else:
        print("❌ Backend is not accessible")
        print()
        print("Troubleshooting steps:")
        print("1. Check if backend container is running:")
        print("   docker-compose ps")
        print()
        print("2. Check backend logs:")
        print("   docker-compose logs -f backend")
        print()
        print("3. Restart backend:")
        print("   docker-compose restart backend")
        print()
        print("4. Check if port 8000 is in use:")
        print("   netstat -tulpn | grep 8000")
        return False

if __name__ == "__main__":
    success = check_backend()
    sys.exit(0 if success else 1)
