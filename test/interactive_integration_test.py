#!/usr/bin/env python3
"""
Interactive Integration Test for Currency + Reporting Agent
==========================================================

This interactive test allows you to manually test the integrated workflow
where Currency Agent calls Reporting Agent via A2A protocol.

Usage:
    python test/interactive_integration_test.py
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
    """Interactive test session for the integrated workflow."""
    print("=" * 80)
    print("  INTERACTIVE INTEGRATION TEST")
    print("  Currency Agent + Reporting Agent")
    print("=" * 80)
    print("This test demonstrates the complete A2A workflow:")
    print("1. User → Currency Agent")
    print("2. Currency Agent → Frankfurter API (exchange rates)")
    print("3. Currency Agent → Reporting Agent (via A2A)")
    print("4. Reporting Agent → Currency Agent (report)")
    print("5. Currency Agent → User (combined response)")
    print()
    
    # Check prerequisites
    print("Prerequisites:")
    print("- Currency Agent: http://localhost:5001")
    print("- Reporting Agent: http://localhost:5002")
    print("- GOOGLE_API_KEY environment variable set")
    print()
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as httpx_client:
            # Initialize currency agent client
            resolver = A2ACardResolver(
                httpx_client=httpx_client,
                base_url='http://localhost:5001',
            )
            
            agent_card = await resolver.get_agent_card()
            client = A2AClient(httpx_client=httpx_client, agent_card=agent_card)
            
            print(f"✅ Connected to: {agent_card.name}")
            print(f"   Description: {agent_card.description}")
            print(f"   Version: {agent_card.version}")
            print()
            
            while True:
                print("-" * 60)
                print("Test Options:")
                print("1. Quick test with sample conversion")
                print("2. Enter custom currency conversion")
                print("3. Test streaming response")
                print("4. Test multi-turn conversation")
                print("5. Send custom message")
                print("6. Exit")
                print("-" * 60)
                
                choice = input("Enter your choice (1-6): ").strip()
                
                if choice == '1':
                    await test_sample_conversion(client)
                elif choice == '2':
                    await test_custom_conversion(client)
                elif choice == '3':
                    await test_streaming(client)
                elif choice == '4':
                    await test_multi_turn(client)
                elif choice == '5':
                    await test_custom_message(client)
                elif choice == '6':
                    print("Goodbye!")
                    break
                else:
                    print("Invalid choice. Please try again.")
                    
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nMake sure both agents are running:")
        print("  Terminal 1: GOOGLE_API_KEY=your_key python -m currency_agent --host localhost --port 5001")
        print("  Terminal 2: GOOGLE_API_KEY=your_key python -m reporting_agent --host localhost --port 5002")
        sys.exit(1)


async def test_sample_conversion(client: A2AClient):
    """Test with a predefined sample conversion."""
    print(f"\n📊 Testing sample conversion: 100 USD to EUR")
    
    message = "Convert 100 USD to EUR and provide a detailed analysis"
    await send_message(client, message)


async def test_custom_conversion(client: A2AClient):
    """Test with user-provided conversion data."""
    print("\n📝 Enter conversion details:")
    
    try:
        amount = input("Amount (e.g., 100): ").strip()
        from_currency = input("From currency (e.g., USD): ").strip().upper()
        to_currency = input("To currency (e.g., EUR): ").strip().upper()
        
        if not amount or not from_currency or not to_currency:
            print("❌ All fields are required. Skipping.")
            return
        
        message = f"Convert {amount} {from_currency} to {to_currency} and provide a comprehensive report"
        print(f"\n📊 Testing conversion: {amount} {from_currency} → {to_currency}")
        await send_message(client, message)
        
    except Exception as e:
        print(f"❌ Error: {e}")


async def test_streaming(client: A2AClient):
    """Test streaming response to see the workflow in real-time."""
    print(f"\n🔄 Testing streaming response...")
    print("This will show the workflow steps in real-time:")
    print("1. Currency Agent fetches exchange rates")
    print("2. Currency Agent calls Reporting Agent")
    print("3. Final integrated response")
    
    message = "Convert 250 GBP to JPY with detailed analysis"
    
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
        print(f"\n📤 Streaming Request: {message}")
        print("🚀 Starting streaming...")
        stream_response = client.send_message_streaming(streaming_request)
        
        chunk_count = 0
        async for chunk in stream_response:
            chunk_count += 1
            result = chunk.root.result
            
            if hasattr(result, 'kind'):
                if result.kind == 'status-update':
                    status_msg = "Unknown status"
                    if hasattr(result.status, 'message') and result.status.message:
                        status_msg = result.status.message.parts[0].text
                    
                    print(f"🔄 [{chunk_count}] {result.status.state}: {status_msg}")
                    
                    # Identify workflow steps
                    if "exchange rates" in status_msg.lower():
                        print("    🔍 Step 1: Fetching exchange rates from Frankfurter API")
                    elif "report" in status_msg.lower():
                        print("    📊 Step 2: Calling Reporting Agent via A2A protocol")
                    elif "processing" in status_msg.lower():
                        print("    ⚙️  Step 3: Processing and combining results")
                        
                elif result.kind == 'artifact-update':
                    print(f"📄 [{chunk_count}] Final Result: {result.artifact.name}")
                    if result.artifact.parts:
                        for part in result.artifact.parts:
                            if hasattr(part, 'text'):
                                print(f"    📝 Content: {part.text[:200]}...")
                                
                                # Check for integration success
                                content = part.text.lower()
                                if "exchange rate" in content and "report" in content:
                                    print("    ✨ SUCCESS: Response contains both exchange rate AND report!")
            else:
                print(f"📦 [{chunk_count}] Final Status: {result.status.state}")
        
        print(f"✅ Streaming completed with {chunk_count} chunks")
        
    except Exception as e:
        print(f"❌ Streaming failed: {e}")


async def test_multi_turn(client: A2AClient):
    """Test multi-turn conversation."""
    print(f"\n💬 Testing multi-turn conversation...")
    
    # Start with incomplete request
    print("👤 Starting with incomplete request...")
    
    request1 = SendMessageRequest(
        id=str(uuid4()),
        params=MessageSendParams(
            message={
                'role': 'user',
                'parts': [{'kind': 'text', 'text': 'I need currency conversion help'}],
                'messageId': uuid4().hex,
            }
        )
    )
    
    try:
        print("📤 User: I need currency conversion help")
        response1 = await client.send_message(request1)
        
        result1 = response1.root.result
        print(f"🤖 Currency Agent: {result1.status.state}")
        
        if hasattr(result1.status, 'message') and result1.status.message:
            agent_response = result1.status.message.parts[0].text
            print(f"    Response: {agent_response}")
        
        # If agent asks for more info, provide it
        if result1.status.state == 'input-required':
            print("\n👤 Providing specific details...")
            
            task_id = result1.id
            context_id = result1.contextId
            
            follow_up = input("Enter your conversion request (e.g., '50 USD to CAD'): ").strip()
            if not follow_up:
                follow_up = "50 USD to CAD"
            
            request2 = SendMessageRequest(
                id=str(uuid4()),
                params=MessageSendParams(
                    message={
                        'role': 'user',
                        'parts': [{'kind': 'text', 'text': follow_up}],
                        'messageId': uuid4().hex,
                        'taskId': task_id,
                        'contextId': context_id,
                    }
                )
            )
            
            print(f"📤 User: {follow_up}")
            response2 = await client.send_message(request2)
            
            result2 = response2.root.result
            print(f"🤖 Currency Agent: {result2.status.state}")
            
            if hasattr(result2, 'artifacts') and result2.artifacts:
                for artifact in result2.artifacts:
                    print(f"📄 Generated: {artifact.name}")
                    if artifact.parts:
                        for part in artifact.parts:
                            if hasattr(part, 'text'):
                                print(f"    📝 Content: {part.text[:300]}...")
        
        print("✅ Multi-turn conversation completed")
        
    except Exception as e:
        print(f"❌ Multi-turn test failed: {e}")


async def test_custom_message(client: A2AClient):
    """Test with a custom message."""
    print("\n✏️ Enter your custom message:")
    message = input("Message: ").strip()
    
    if not message:
        print("❌ Empty message. Skipping.")
        return
    
    await send_message(client, message)


async def send_message(client: A2AClient, message: str):
    """Send a message to the currency agent and display the response."""
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
        print(f"\n📤 Sending: {message}")
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
                            # Show full content for interactive testing
                            print(part.text)
                            
                            # Analyze the response
                            content = part.text.lower()
                            if "exchange rate" in content and ("report" in content or "analysis" in content):
                                print("\n✨ SUCCESS: Integrated response with exchange rate AND report!")
                            elif "exchange rate" in content:
                                print("\n⚠️  Response contains exchange rate but may be missing report")
                            elif "report" in content:
                                print("\n⚠️  Response contains report but may be missing exchange rate")
        
        if hasattr(result.status, 'message') and result.status.message:
            print(f"💬 Agent Message: {result.status.message.parts[0].text}")
        
        print("✅ Message sent successfully")
        
    except Exception as e:
        print(f"❌ Failed to send message: {e}")


if __name__ == '__main__':
    asyncio.run(interactive_test()) 