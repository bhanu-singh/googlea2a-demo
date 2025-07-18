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


PUBLIC_AGENT_CARD_PATH = '/.well-known/agent.json'


def print_separator(title: str):
    """Print a formatted separator with title."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_json_response(response_data: dict, title: str = "Response"):
    """Print JSON response in a formatted way."""
    print(f"\n{title}:")
    print(json.dumps(response_data, indent=2))


async def test_agent_card(resolver: A2ACardResolver, base_url: str) -> AgentCard:
    """Test fetching the agent card."""
    print_separator("TESTING AGENT CARD")
    
    try:
        print(f"Fetching agent card from: {base_url}{PUBLIC_AGENT_CARD_PATH}")
        agent_card = await resolver.get_agent_card()
        
        print(f"✅ Successfully fetched agent card:")
        print(f"   Name: {agent_card.name}")
        print(f"   Description: {agent_card.description}")
        print(f"   Version: {agent_card.version}")
        print(f"   Skills: {len(agent_card.skills)} skill(s)")
        
        for skill in agent_card.skills:
            print(f"     - {skill.name}: {skill.description}")
        
        print(f"   Capabilities: Streaming={agent_card.capabilities.streaming}, Push={agent_card.capabilities.pushNotifications}")
        
        return agent_card
        
    except Exception as e:
        print(f"❌ Failed to fetch agent card: {e}")
        raise


async def test_basic_report_generation(client: A2AClient) -> None:
    """Test basic report generation functionality."""
    print_separator("TESTING BASIC REPORT GENERATION")
    
    # Sample conversion data
    conversion_data = {
        'from': 'USD',
        'to': 'EUR',
        'rate': 0.85,
        'raw': {
            'date': '2024-01-15',
            'base': 'USD',
            'rates': {'EUR': 0.85}
        }
    }
    
    message_text = f"Generate a detailed report for this currency conversion: {json.dumps(conversion_data, indent=2)}"
    
    request = SendMessageRequest(
        id=str(uuid4()),
        params=MessageSendParams(
            message={
                'role': 'user',
                'parts': [{'kind': 'text', 'text': message_text}],
                'messageId': uuid4().hex,
            }
        )
    )
    
    try:
        print(f"Sending request: {message_text[:100]}...")
        response = await client.send_message(request)
        
        result = response.root.result
        print(f"✅ Task Status: {result.status.state}")
        
        if hasattr(result, 'artifacts') and result.artifacts:
            print(f"📄 Generated {len(result.artifacts)} artifact(s):")
            for artifact in result.artifacts:
                print(f"   - {artifact.name}")
                if artifact.parts:
                    for part in artifact.parts:
                        if hasattr(part, 'text'):
                            print(f"     Content: {part.text[:200]}...")
        
        print_json_response(response.model_dump(mode='json', exclude_none=True), "Full Response")
        
    except Exception as e:
        print(f"❌ Failed to generate report: {e}")


async def test_summary_generation(client: A2AClient) -> None:
    """Test summary generation functionality."""
    print_separator("TESTING SUMMARY GENERATION")
    
    conversion_data = {
        'from': 'GBP',
        'to': 'JPY',
        'rate': 150.25,
        'raw': {
            'date': '2024-01-15',
            'base': 'GBP',
            'rates': {'JPY': 150.25}
        }
    }
    
    message_text = f"Create a brief summary for this conversion: {json.dumps(conversion_data)}"
    
    request = SendMessageRequest(
        id=str(uuid4()),
        params=MessageSendParams(
            message={
                'role': 'user',
                'parts': [{'kind': 'text', 'text': message_text}],
                'messageId': uuid4().hex,
            }
        )
    )
    
    try:
        print(f"Sending request: {message_text}")
        response = await client.send_message(request)
        
        result = response.root.result
        print(f"✅ Task Status: {result.status.state}")
        
        if hasattr(result, 'artifacts') and result.artifacts:
            for artifact in result.artifacts:
                print(f"📄 {artifact.name}:")
                if artifact.parts:
                    for part in artifact.parts:
                        if hasattr(part, 'text'):
                            print(f"   {part.text}")
        
    except Exception as e:
        print(f"❌ Failed to generate summary: {e}")


async def test_streaming_response(client: A2AClient) -> None:
    """Test streaming response functionality."""
    print_separator("TESTING STREAMING RESPONSE")
    
    conversion_data = {
        'from': 'CAD',
        'to': 'AUD',
        'rate': 1.12,
        'raw': {
            'date': '2024-01-15',
            'base': 'CAD',
            'rates': {'AUD': 1.12}
        }
    }
    
    message_text = f"Generate a comprehensive report for: {json.dumps(conversion_data)}"
    
    streaming_request = SendStreamingMessageRequest(
        id=str(uuid4()),
        params=MessageSendParams(
            message={
                'role': 'user',
                'parts': [{'kind': 'text', 'text': message_text}],
                'messageId': uuid4().hex,
            }
        )
    )
    
    try:
        print(f"Starting streaming request...")
        stream_response = client.send_message_streaming(streaming_request)
        
        chunk_count = 0
        async for chunk in stream_response:
            chunk_count += 1
            result = chunk.root.result
            
            if hasattr(result, 'kind'):
                if result.kind == 'status-update':
                    print(f"🔄 Status Update {chunk_count}: {result.status.state}")
                    if hasattr(result.status, 'message') and result.status.message:
                        print(f"   Message: {result.status.message.parts[0].text}")
                elif result.kind == 'artifact-update':
                    print(f"📄 Artifact Update {chunk_count}: {result.artifact.name}")
                    if result.artifact.parts:
                        for part in result.artifact.parts:
                            if hasattr(part, 'text'):
                                print(f"   Content: {part.text[:100]}...")
            else:
                print(f"📦 Chunk {chunk_count}: {result.status.state}")
        
        print(f"✅ Streaming completed with {chunk_count} chunks")
        
    except Exception as e:
        print(f"❌ Streaming failed: {e}")


async def test_multi_turn_conversation(client: A2AClient) -> None:
    """Test multi-turn conversation functionality."""
    print_separator("TESTING MULTI-TURN CONVERSATION")
    
    # First message
    request1 = SendMessageRequest(
        id=str(uuid4()),
        params=MessageSendParams(
            message={
                'role': 'user',
                'parts': [{'kind': 'text', 'text': 'Can you help me with a currency conversion report?'}],
                'messageId': uuid4().hex,
            }
        )
    )
    
    try:
        print("👤 User: Can you help me with a currency conversion report?")
        response1 = await client.send_message(request1)
        
        result1 = response1.root.result
        print(f"🤖 Agent: {result1.status.state}")
        
        if hasattr(result1.status, 'message') and result1.status.message:
            print(f"   {result1.status.message.parts[0].text}")
        
        # If the agent is asking for input, provide conversion data
        if result1.status.state == 'input-required':
            task_id = result1.id
            context_id = result1.contextId
            
            conversion_data = {
                'from': 'USD',
                'to': 'INR',
                'rate': 83.25,
                'raw': {
                    'date': '2024-01-15',
                    'base': 'USD',
                    'rates': {'INR': 83.25}
                }
            }
            
            # Second message with conversion data
            request2 = SendMessageRequest(
                id=str(uuid4()),
                params=MessageSendParams(
                    message={
                        'role': 'user',
                        'parts': [{'kind': 'text', 'text': f'Here is the conversion data: {json.dumps(conversion_data)}'}],
                        'messageId': uuid4().hex,
                        'taskId': task_id,
                        'contextId': context_id,
                    }
                )
            )
            
            print(f"👤 User: Here is the conversion data: {json.dumps(conversion_data)}")
            response2 = await client.send_message(request2)
            
            result2 = response2.root.result
            print(f"🤖 Agent: {result2.status.state}")
            
            if hasattr(result2, 'artifacts') and result2.artifacts:
                for artifact in result2.artifacts:
                    print(f"📄 Generated: {artifact.name}")
                    if artifact.parts:
                        for part in artifact.parts:
                            if hasattr(part, 'text'):
                                print(f"   {part.text[:200]}...")
        
        print("✅ Multi-turn conversation completed")
        
    except Exception as e:
        print(f"❌ Multi-turn conversation failed: {e}")


async def test_error_handling(client: A2AClient) -> None:
    """Test error handling with invalid input."""
    print_separator("TESTING ERROR HANDLING")
    
    # Test with invalid/incomplete data
    request = SendMessageRequest(
        id=str(uuid4()),
        params=MessageSendParams(
            message={
                'role': 'user',
                'parts': [{'kind': 'text', 'text': 'Generate a report for invalid data: {"invalid": "data"}'}],
                'messageId': uuid4().hex,
            }
        )
    )
    
    try:
        print("Sending request with invalid data...")
        response = await client.send_message(request)
        
        result = response.root.result
        print(f"📊 Response Status: {result.status.state}")
        
        if hasattr(result.status, 'message') and result.status.message:
            print(f"   Message: {result.status.message.parts[0].text}")
        
        print("✅ Error handling test completed")
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")


async def main() -> None:
    """Main test function."""
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    base_url = 'http://localhost:5002'
    
    print_separator("REPORTING AGENT TEST CLIENT")
    print(f"Testing Reporting Agent at: {base_url}")
    print(f"Make sure the reporting agent is running with:")
    print(f"  GOOGLE_API_KEY=your_key python -m reporting_agent --host localhost --port 5002")
    
    async with httpx.AsyncClient(timeout=30.0) as httpx_client:
        try:
            # Initialize resolver and test agent card
            resolver = A2ACardResolver(httpx_client=httpx_client, base_url=base_url)
            agent_card = await test_agent_card(resolver, base_url)
            
            # Initialize client
            client = A2AClient(httpx_client=httpx_client, agent_card=agent_card)
            
            # Run all tests
            await test_basic_report_generation(client)
            await test_summary_generation(client)
            await test_streaming_response(client)
            await test_multi_turn_conversation(client)
            await test_error_handling(client)
            
            print_separator("ALL TESTS COMPLETED")
            print("✅ All tests completed successfully!")
            
        except Exception as e:
            print_separator("TEST FAILED")
            print(f"❌ Test suite failed: {e}")
            raise


if __name__ == '__main__':
    asyncio.run(main()) 