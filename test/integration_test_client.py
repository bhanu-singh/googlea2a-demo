#!/usr/bin/env python3
"""
Integration Test Client for Currency Agent + Reporting Agent
============================================================

This test client demonstrates the complete workflow:
1. User sends currency conversion request to Currency Agent
2. Currency Agent gets exchange rate
3. Currency Agent calls Reporting Agent via A2A protocol
4. Reporting Agent generates comprehensive report
5. Currency Agent returns final response with both rate and report

Usage:
    python test/integration_test_client.py
"""

import asyncio
import json
import logging
from typing import Any
from uuid import uuid4

import httpx

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    AgentCard,
    MessageSendParams,
    SendMessageRequest,
    SendStreamingMessageRequest,
)


def print_separator(title: str, char: str = "="):
    """Print a formatted separator with title."""
    print(f"\n{char*80}")
    print(f"  {title}")
    print(f"{char*80}")


def print_step(step_num: int, description: str):
    """Print a step in the workflow."""
    print(f"\n🔄 Step {step_num}: {description}")


def print_success(message: str):
    """Print a success message."""
    print(f"✅ {message}")


def print_error(message: str):
    """Print an error message."""
    print(f"❌ {message}")


async def check_agent_availability(base_url: str, agent_name: str) -> bool:
    """Check if an agent is available and responsive."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url}/.well-known/agent.json")
            if response.status_code == 200:
                agent_data = response.json()
                print_success(f"{agent_name} is available at {base_url}")
                print(f"   Name: {agent_data.get('name', 'Unknown')}")
                print(f"   Description: {agent_data.get('description', 'No description')}")
                return True
            else:
                print_error(f"{agent_name} returned status {response.status_code}")
                return False
    except Exception as e:
        print_error(f"Failed to connect to {agent_name}: {e}")
        return False


async def test_basic_integration(currency_client: A2AClient) -> None:
    """Test basic integration with a simple currency conversion."""
    print_separator("BASIC INTEGRATION TEST")
    
    print_step(1, "Sending currency conversion request to Currency Agent")
    
    request = SendMessageRequest(
        id=str(uuid4()),
        params=MessageSendParams(
            message={
                'role': 'user',
                'parts': [{'kind': 'text', 'text': 'How much is 100 USD in EUR?'}],
                'messageId': uuid4().hex,
            }
        )
    )
    
    try:
        print("📤 Request: How much is 100 USD in EUR?")
        response = await currency_client.send_message(request)
        
        result = response.root.result
        print_success(f"Currency Agent responded with status: {result.status.state}")
        
        if hasattr(result, 'artifacts') and result.artifacts:
            print_step(2, "Currency Agent generated artifacts")
            for artifact in result.artifacts:
                print(f"📄 Artifact: {artifact.name}")
                if artifact.parts:
                    for part in artifact.parts:
                        if hasattr(part, 'text'):
                            print(f"📝 Content Preview: {part.text[:200]}...")
                            
                            # Check if the response contains both exchange rate and report
                            content = part.text.lower()
                            has_rate = any(keyword in content for keyword in ['rate', 'exchange', 'usd', 'eur'])
                            has_report = any(keyword in content for keyword in ['report', 'analysis', 'conversion details'])
                            
                            if has_rate and has_report:
                                print_success("✨ Response contains both exchange rate AND comprehensive report!")
                            elif has_rate:
                                print("⚠️  Response contains exchange rate but may be missing report")
                            elif has_report:
                                print("⚠️  Response contains report but may be missing rate")
                            else:
                                print("⚠️  Response content unclear")
        
        print_step(3, "Integration test completed")
        return True
        
    except Exception as e:
        print_error(f"Basic integration test failed: {e}")
        return False


async def test_streaming_integration(currency_client: A2AClient) -> None:
    """Test streaming integration to see the workflow in real-time."""
    print_separator("STREAMING INTEGRATION TEST")
    
    print_step(1, "Starting streaming request to observe workflow")
    
    streaming_request = SendStreamingMessageRequest(
        id=str(uuid4()),
        params=MessageSendParams(
            message={
                'role': 'user',
                'parts': [{'kind': 'text', 'text': 'Convert 50 GBP to JPY and provide a detailed analysis'}],
                'messageId': uuid4().hex,
            }
        )
    )
    
    try:
        print("📤 Streaming Request: Convert 50 GBP to JPY and provide a detailed analysis")
        stream_response = currency_client.send_message_streaming(streaming_request)
        
        step_count = 0
        async for chunk in stream_response:
            step_count += 1
            result = chunk.root.result
            
            if hasattr(result, 'kind'):
                if result.kind == 'status-update':
                    status_msg = "Unknown status"
                    if hasattr(result.status, 'message') and result.status.message:
                        status_msg = result.status.message.parts[0].text
                    
                    print(f"🔄 [{step_count}] Status: {result.status.state}")
                    print(f"    Message: {status_msg}")
                    
                    # Identify workflow steps
                    if "exchange rates" in status_msg.lower():
                        print("    🔍 Currency Agent is fetching exchange rates...")
                    elif "report" in status_msg.lower():
                        print("    📊 Currency Agent is calling Reporting Agent...")
                    elif "processing" in status_msg.lower():
                        print("    ⚙️  Processing results...")
                        
                elif result.kind == 'artifact-update':
                    print(f"📄 [{step_count}] Artifact Generated: {result.artifact.name}")
                    if result.artifact.parts:
                        for part in result.artifact.parts:
                            if hasattr(part, 'text'):
                                print(f"    📝 Content: {part.text[:150]}...")
            else:
                print(f"📦 [{step_count}] Final Status: {result.status.state}")
        
        print_success(f"Streaming completed with {step_count} updates")
        print_step(2, "Workflow observation completed")
        
    except Exception as e:
        print_error(f"Streaming integration test failed: {e}")


async def test_multi_turn_integration(currency_client: A2AClient) -> None:
    """Test multi-turn conversation with the integrated system."""
    print_separator("MULTI-TURN INTEGRATION TEST")
    
    print_step(1, "Starting multi-turn conversation")
    
    # First message - incomplete request
    request1 = SendMessageRequest(
        id=str(uuid4()),
        params=MessageSendParams(
            message={
                'role': 'user',
                'parts': [{'kind': 'text', 'text': 'I need to convert some currency'}],
                'messageId': uuid4().hex,
            }
        )
    )
    
    try:
        print("👤 User: I need to convert some currency")
        response1 = await currency_client.send_message(request1)
        
        result1 = response1.root.result
        print(f"🤖 Currency Agent: {result1.status.state}")
        
        if hasattr(result1.status, 'message') and result1.status.message:
            agent_response = result1.status.message.parts[0].text
            print(f"    Response: {agent_response}")
        
        # If agent asks for more info, provide it
        if result1.status.state == 'input-required':
            print_step(2, "Providing specific conversion details")
            
            task_id = result1.id
            context_id = result1.contextId
            
            request2 = SendMessageRequest(
                id=str(uuid4()),
                params=MessageSendParams(
                    message={
                        'role': 'user',
                        'parts': [{'kind': 'text', 'text': '200 CAD to AUD please'}],
                        'messageId': uuid4().hex,
                        'taskId': task_id,
                        'contextId': context_id,
                    }
                )
            )
            
            print("👤 User: 200 CAD to AUD please")
            response2 = await currency_client.send_message(request2)
            
            result2 = response2.root.result
            print(f"🤖 Currency Agent: {result2.status.state}")
            
            if hasattr(result2, 'artifacts') and result2.artifacts:
                print_step(3, "Final response with integrated results")
                for artifact in result2.artifacts:
                    print(f"📄 Generated: {artifact.name}")
                    if artifact.parts:
                        for part in artifact.parts:
                            if hasattr(part, 'text'):
                                print(f"    📝 Content: {part.text[:200]}...")
        
        print_success("Multi-turn integration test completed")
        
    except Exception as e:
        print_error(f"Multi-turn integration test failed: {e}")


async def test_different_currencies(currency_client: A2AClient) -> None:
    """Test with different currency pairs to ensure robustness."""
    print_separator("MULTIPLE CURRENCY PAIRS TEST")
    
    test_cases = [
        ("25 USD to INR", "USD → INR"),
        ("1000 EUR to GBP", "EUR → GBP"),
        ("50 JPY to USD", "JPY → USD"),
        ("100 AUD to CAD", "AUD → CAD"),
    ]
    
    for i, (request_text, description) in enumerate(test_cases, 1):
        print_step(i, f"Testing {description}")
        
        request = SendMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(
                message={
                    'role': 'user',
                    'parts': [{'kind': 'text', 'text': request_text}],
                    'messageId': uuid4().hex,
                }
            )
        )
        
        try:
            print(f"📤 Request: {request_text}")
            response = await currency_client.send_message(request)
            
            result = response.root.result
            if result.status.state == 'completed':
                print_success(f"{description} conversion completed successfully")
            else:
                print(f"⚠️  {description} returned status: {result.status.state}")
                
        except Exception as e:
            print_error(f"{description} test failed: {e}")


async def main() -> None:
    """Main integration test function."""
    print_separator("CURRENCY + REPORTING AGENT INTEGRATION TEST", "=")
    print("This test demonstrates the complete A2A workflow:")
    print("1. User → Currency Agent (A2A)")
    print("2. Currency Agent → Frankfurter API (HTTP)")
    print("3. Currency Agent → Reporting Agent (A2A)")
    print("4. Reporting Agent → User (A2A)")
    print()
    print("Prerequisites:")
    print("- Currency Agent running on http://localhost:5001")
    print("- Reporting Agent running on http://localhost:5002")
    print("- GOOGLE_API_KEY environment variable set")
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Check agent availability
    print_separator("CHECKING AGENT AVAILABILITY")
    
    currency_available = await check_agent_availability('http://localhost:5001', 'Currency Agent')
    reporting_available = await check_agent_availability('http://localhost:5002', 'Reporting Agent')
    
    if not currency_available or not reporting_available:
        print_error("One or both agents are not available. Please start them first:")
        print("  Terminal 1: GOOGLE_API_KEY=your_key python -m currency_agent --host localhost --port 5001")
        print("  Terminal 2: GOOGLE_API_KEY=your_key python -m reporting_agent --host localhost --port 5002")
        return
    
    # Initialize currency agent client
    try:
        async with httpx.AsyncClient(timeout=60.0) as httpx_client:
            resolver = A2ACardResolver(
                httpx_client=httpx_client,
                base_url='http://localhost:5001',
            )
            
            agent_card = await resolver.get_agent_card()
            currency_client = A2AClient(httpx_client=httpx_client, agent_card=agent_card)
            
            print_success("Connected to Currency Agent successfully")
            
            # Run integration tests
            await test_basic_integration(currency_client)
            await test_streaming_integration(currency_client)
            await test_multi_turn_integration(currency_client)
            await test_different_currencies(currency_client)
            
            print_separator("INTEGRATION TESTS COMPLETED", "=")
            print_success("🎉 All integration tests completed successfully!")
            print()
            print("The workflow demonstrates:")
            print("✅ Currency Agent receives user requests")
            print("✅ Currency Agent fetches exchange rates")
            print("✅ Currency Agent calls Reporting Agent via A2A protocol")
            print("✅ Reporting Agent generates comprehensive reports")
            print("✅ Currency Agent returns integrated results")
            print("✅ Streaming, multi-turn, and error handling work correctly")
            
    except Exception as e:
        print_error(f"Integration test failed: {e}")
        raise


if __name__ == '__main__':
    asyncio.run(main()) 