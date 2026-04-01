#!/usr/bin/env python3
"""
Test script for HeyReach webhook endpoint.
Usage: python test_webhook.py
"""
import requests
import json

WEBHOOK_URL = "http://localhost:8000/api/webhook/heyreach"

# Sample webhook payload
test_payload = {
    "event": "EVERY_MESSAGE_REPLY_RECEIVED",
    "data": {
        "conversationId": "test-conv-123",
        "linkedInAccountId": 12345,
        "message": {
            "id": "msg-456",
            "body": "Thanks for reaching out! I'd love to learn more.",
            "createdAt": "2026-03-31T10:00:00Z"
        },
        "correspondent": {
            "firstName": "John",
            "lastName": "Doe",
            "companyName": "Acme Corp",
            "position": "CEO",
            "location": "Miami, FL",
            "profileUrl": "https://www.linkedin.com/in/johndoe",
            "headline": "CEO at Acme Corp"
        }
    }
}

print("=" * 60)
print("Testing HeyReach Webhook Endpoint")
print("=" * 60)
print(f"URL: {WEBHOOK_URL}")
print(f"Payload: {json.dumps(test_payload, indent=2)}")
print("-" * 60)

try:
    response = requests.post(WEBHOOK_URL, json=test_payload, timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
except requests.exceptions.ConnectionError:
    print("ERROR: Could not connect to backend. Is it running on port 8000?")
except requests.exceptions.Timeout:
    print("ERROR: Request timed out")
except Exception as e:
    print(f"ERROR: {e}")

print("=" * 60)
