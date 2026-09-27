import sys
import os

# Adjust path to find agents modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.notification_agent import NotificationAgent

def test_deduplication():
    print("🧪 Testing Alert Deduplication and Types...")
    agent = NotificationAgent()
    
    # 1. Send First Alert (Should Send)
    print("\n[Step 1] Sending First Alert (Rain)...")
    resp1 = agent.send_alert("TestDist", 3, alert_type="Rain", is_test=True)
    print(f"Response: {resp1['response_text']}")
    
    if "Sent" not in resp1['response_text'] and "sent" not in resp1['response_text']:
        print("❌ FAILED: Expected alert to be sent.")
    
    # 2. Send Duplicate Alert (Should Skip)
    print("\n[Step 2] Sending Duplicate Alert (Rain)...")
    resp2 = agent.send_alert("TestDist", 3, alert_type="Rain", is_test=True)
    print(f"Response: {resp2['response_text']}")
    
    if "already sent" not in resp2['response_text']:
        print("❌ FAILED: Expected alert to be skipped.")
    else:
        print("✅ SUCCESS: Duplicate alert skipped.")

    # 3. Send Different Type Alert (Should Send)
    print("\n[Step 3] Sending Different Type Alert (Cloud Burst)...")
    resp3 = agent.send_alert("TestDist", 3, alert_type="Cloud Burst", is_test=True)
    print(f"Response: {resp3['response_text']}")
    
    if "Sent" not in resp3['response_text'] and "sent" not in resp3['response_text']:
        print("❌ FAILED: Expected new alert type to be sent.")
    else:
        print("✅ SUCCESS: Different alert type sent.")

if __name__ == "__main__":
    test_deduplication()
