import requests
import json

# Test API endpoint
BASE_URL = "http://localhost:8000"

# 1. Login
print("=== 1. LOGIN ===")
login_data = {
    "username": "admin",
    "password": ""
}
response = requests.post(f"{BASE_URL}/token", data=login_data)
print(f"Status: {response.status_code}")

if response.status_code == 200:
    token_data = response.json()
    token = token_data["access_token"]
    print(f"Token: {token[:30]}...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Get History
    print("\n=== 2. GET HISTORY ===")
    response = requests.get(f"{BASE_URL}/api/history", headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        history = response.json()
        print(f"Found {len(history)} transcriptions")
        
        if history:
            # Test first completed task
            completed = [t for t in history if t['status'] == 'completed']
            if completed:
                task_id = completed[0]['task_id']
                print(f"\nTesting task: {task_id}")
                print(f"Filename: {completed[0]['filename']}")
                print(f"Summary in history: {'YES' if completed[0].get('summary') else 'NO'}")
                print(f"Topics in history: {'YES' if completed[0].get('topics') else 'NO'}")
                
                # 3. Get Result
                print("\n=== 3. GET RESULT ===")
                response = requests.get(f"{BASE_URL}/api/result/{task_id}", headers=headers)
                print(f"Status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    print("\nAPI Response Keys:", list(result.keys()))
                    print(f"\nSummary in response: {'YES' if 'summary' in result else 'NO'}")
                    if 'summary' in result:
                        print(f"Summary value: {result['summary'][:100] if result['summary'] else 'NULL'}")
                    
                    print(f"\nTopics in response: {'YES' if 'topics' in result else 'NO'}")
                    if 'topics' in result:
                        print(f"Topics value: {result['topics']}")
                    
                    print("\n=== FULL RESPONSE ===")
                    print(json.dumps(result, indent=2, ensure_ascii=False))
                else:
                    print(f"Error: {response.text}")
else:
    print(f"Login failed: {response.text}")
