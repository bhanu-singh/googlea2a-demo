#!/usr/bin/env python3
"""
Interactive test client for the Reporting Agent.
This allows you to manually test the agent with custom inputs.
"""

import asyncio
import json
import sys
from typing import Any
from uuid import uuid4

import httpx

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    MessageSendParams,
    SendMessageRequest,
    SendStreamingMessageRequest,
)


async def interactive_test():
    """Interactive test session."""
    base_url = 'http://localhost:5002'
    
    print("=" * 60)
    print("  REPORTING AGENT INTERACTIVE TEST")
    print("=" * 60)
    print(f"Connecting to: {base_url}")
    print("Make sure the reporting agent is running with:")
    print("  GOOGLE_API_KEY=your_key python -m reporting_agent --host localhost --port 5002")
    print()
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as httpx_client:
            # Initialize resolver and client
            resolver = A2ACardResolver(httpx_client=httpx_client, base_url=base_url)
            agent_card = await resolver.get_agent_card()
            client = A2AClient(httpx_client=httpx_client, agent_card=agent_card)
            
            print(f"✅ Connected to: {agent_card.name}")
            print(f"   Description: {agent_card.description}")
            print(f"   Version: {agent_card.version}")
            print()
            
            # Sample conversion data for easy testing
            sample_data = {
                'from': 'USD',
                'to': 'EUR',
                'rate': 0.85,
                'raw': {
                    'date': '2024-01-15',
                    'base': 'USD',
                    'rates': {'EUR': 0.85}
                }
            }
            
            while True:
                print("-" * 40)
                print("Options:")
                print("1. Test with sample data")
                print("2. Enter custom conversion data")
                print("3. Test streaming response")
                print("4. Test with custom message")
                print("5. Exit")
                print("-" * 40)
                
                choice = input("Enter your choice (1-5): ").strip()
                
                if choice == '1':
                    await test_with_sample_data(client, sample_data)
                elif choice == '2':
                    await test_with_custom_data(client)
                elif choice == '3':
                    await test_streaming(client, sample_data)
                elif choice == '4':
                    await test_custom_message(client)
                elif choice == '5':
                    print("Goodbye!")
                    break
                else:
                    print("Invalid choice. Please try again.")
                    
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


async def test_with_sample_data(client: A2AClient, sample_data: dict):
    """Test with predefined sample data."""
    print(f"\n📊 Testing with sample data:")
    print(json.dumps(sample_data, indent=2))
    
    message = f"Generate a detailed report for this currency conversion: {json.dumps(sample_data)}"
    await send_message(client, message)


async def test_with_custom_data(client: A2AClient):
    """Test with user-provided conversion data."""
    print("\n📝 Enter conversion data:")
    
    try:
        from_currency = input("From currency (e.g., USD): ").strip().upper()
        to_currency = input("To currency (e.g., EUR): ").strip().upper()
        rate = float(input("Exchange rate (e.g., 0.85): ").strip())
        date = input("Date (e.g., 2024-01-15) or press Enter for today: ").strip()
        
        if not date:
            from datetime import date as dt
            date = dt.today().strftime('%Y-%m-%d')
        
        conversion_data = {
            'from': from_currency,
            'to': to_currency,
            'rate': rate,
            'raw': {
                'date': date,
                'base': from_currency,
                'rates': {to_currency: rate}
            }
        }
        
        print(f"\n📊 Using conversion data:")
        print(json.dumps(conversion_data, indent=2))
        
        message = f"Generate a comprehensive report for this currency conversion: {json.dumps(conversion_data)}"
        await send_message(client, message)
        
    except ValueError as e:
        print(f"❌ Invalid input: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")


async def test_streaming(client: A2AClient, sample_data: dict):
    """Test streaming response."""
    print(f"\n🔄 Testing streaming response with sample data...")
    
    message = f"Generate a report for: {json.dumps(sample_data)}"
    
    streaming_request = SendStreamingMessageRequest(
        id=str(uuid4()),
        params=MessageSendParams(
            message={
                'role': 'user',
                'parts': [{'kind': 'text', 'text': message}],
                'messageId': uuid4().hex,
            }
        )
    )
    
    try:
        print("🚀 Starting streaming...")
        stream_response = client.send_message_streaming(streaming_request)
        
        chunk_count = 0
        async for chunk in stream_response:
            chunk_count += 1
            result = chunk.root.result
            
            if hasattr(result, 'kind'):
                if result.kind == 'status-update':
                    print(f"🔄 [{chunk_count}] Status: {result.status.state}")
                    if hasattr(result.status, 'message') and result.status.message:
                        print(f"    Message: {result.status.message.parts[0].text}")
                elif result.kind == 'artifact-update':
                    print(f"📄 [{chunk_count}] Artifact: {result.artifact.name}")
                    if result.artifact.parts:
                        for part in result.artifact.parts:
                            if hasattr(part, 'text'):
                                print(f"    Content: {part.text[:100]}...")
            else:
                print(f"📦 [{chunk_count}] Status: {result.status.state}")
        
        print(f"✅ Streaming completed with {chunk_count} chunks")
        
    except Exception as e:
        print(f"❌ Streaming failed: {e}")


async def test_custom_message(client: A2AClient):
    """Test with a custom message."""
    print("\n✏️ Enter your custom message:")
    message = input("Message: ").strip()
    
    if not message:
        print("❌ Empty message. Skipping.")
        return
    
    await send_message(client, message)


async def send_message(client: A2AClient, message: str):
    """Send a message to the agent and display the response."""
    request = SendMessageRequest(
        id=str(uuid4()),
        params=MessageSendParams(
            message={
                'role': 'user',
                'parts': [{'kind': 'text', 'text': message}],
                'messageId': uuid4().hex,
            }
        )
    )
    
    try:
        print(f"\n📤 Sending: {message[:100]}...")
        response = await client.send_message(request)
        
        result = response.root.result
        print(f"📥 Response Status: {result.status.state}")
        
        if hasattr(result, 'artifacts') and result.artifacts:
            print(f"📄 Generated {len(result.artifacts)} artifact(s):")
            for artifact in result.artifacts:
                print(f"\n--- {artifact.name} ---")
                if artifact.parts:
                    for part in artifact.parts:
                        if hasattr(part, 'text'):
                            print(part.text)
        
        if hasattr(result.status, 'message') and result.status.message:
            print(f"💬 Agent Message: {result.status.message.parts[0].text}")
        
        print("✅ Message sent successfully")
        
    except Exception as e:
        print(f"❌ Failed to send message: {e}")


if __name__ == '__main__':
    asyncio.run(interactive_test()) 