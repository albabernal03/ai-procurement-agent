# test_network.py
import requests
import socket

print("="*60)
print("NETWORK CONNECTIVITY TEST")
print("="*60)

# Test 1: Basic internet
print("\n1. Testing internet connectivity...")
try:
    response = requests.get("https://www.google.com", timeout=5)
    print(f"   ✓ Internet connection OK (status: {response.status_code})")
except Exception as e:
    print(f"   ✗ No internet connection: {e}")

# Test 2: Groq API endpoint
print("\n2. Testing Groq API endpoint...")
try:
    response = requests.get("https://api.groq.com", timeout=10)
    print(f"   ✓ Can reach api.groq.com (status: {response.status_code})")
except requests.exceptions.SSLError as e:
    print(f"   ✗ SSL Error: {e}")
    print(f"   → This might be a corporate proxy/firewall issue")
except requests.exceptions.ConnectionError as e:
    print(f"   ✗ Connection Error: {e}")
    print(f"   → Groq might be blocked by your network")
except Exception as e:
    print(f"   ✗ Cannot reach api.groq.com: {e}")

# Test 3: DNS resolution
print("\n3. Testing DNS resolution...")
try:
    ip = socket.gethostbyname("api.groq.com")
    print(f"   ✓ api.groq.com resolves to {ip}")
except Exception as e:
    print(f"   ✗ DNS resolution failed: {e}")

# Test 4: Check for VPN
print("\n4. Checking for VPN/Proxy...")
try:
    # Get current IP
    response = requests.get("https://api.ipify.org?format=json", timeout=5)
    current_ip = response.json()['ip']
    print(f"   Your public IP: {current_ip}")
    
    # Check if using common VPN ranges
    if current_ip.startswith(('10.', '172.', '192.168.')):
        print(f"   ⚠️  You're using a private IP - likely behind NAT/VPN")
except:
    print(f"   Could not determine IP")

print("\n" + "="*60)