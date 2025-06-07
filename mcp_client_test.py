#!/usr/bin/env python3
"""
Simulate how a real MCP client would interact with pyramid-mcp.
This shows what an AI assistant would experience when using auto-discovered tools.
"""
import asyncio
import httpx
import json

class MCPClientSimulator:
    def __init__(self, base_url="http://localhost:8080/mcp"):
        self.base_url = base_url
        self.request_id = 0
    
    def _next_id(self):
        self.request_id += 1
        return self.request_id
    
    async def call_mcp(self, method, params=None):
        async with httpx.AsyncClient() as client:
            request = {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": method,
                "params": params or {}
            }
            response = await client.post(self.base_url, json=request)
            return response.json()
    
    async def simulate_ai_workflow(self):
        print("🤖 AI Assistant: I need to interact with this Pyramid API via MCP...")
        print()
        
        # Step 1: Discover available tools
        print("1. Discovering available tools...")
        tools_response = await self.call_mcp("tools/list")
        tools = tools_response.get("result", {}).get("tools", [])
        
        # Filter to API tools only
        api_tools = [t for t in tools if 'api' in t['name']]
        print(f"Found {len(api_tools)} API tools:")
        for tool in api_tools:
            print(f"   - {tool['name']}: {tool['description']}")
        print()
        
        # Step 2: Use the hello API tool
        print("2. Using get_api_hello tool...")
        hello_response = await self.call_mcp("tools/call", {
            "name": "get_api_hello", 
            "arguments": {"name": "AI Assistant"}
        })
        
        if "result" in hello_response:
            result = hello_response["result"]["content"][0]["text"]
            print(f"   Response: {result}")
        else:
            print(f"   Error: {hello_response.get('error')}")
        print()
        
        # Step 3: Use the users API tool
        print("3. Using list_api_users tool...")
        users_response = await self.call_mcp("tools/call", {
            "name": "list_api_users",
            "arguments": {}
        })
        
        if "result" in users_response:
            result = users_response["result"]["content"][0]["text"]
            print(f"   Response: {result}")
        else:
            print(f"   Error: {users_response.get('error')}")
        print()
        
        # Step 4: Analysis
        print("🔍 Analysis:")
        print("   - The MCP tools are discovered successfully")
        print("   - Tool schemas are generated from route patterns")
        print("   - However, tools return simulation data instead of actual API results")
        print("   - For production use, the route handler needs to actually call the endpoints")
        print()
        
        # Step 5: Compare with direct API calls
        print("4. Comparing with direct API calls...")
        try:
            async with httpx.AsyncClient() as client:
                # Direct API call to hello endpoint
                direct_hello = await client.get("http://localhost:8080/api/hello?name=AI%20Assistant")
                print(f"   Direct /api/hello: {direct_hello.json()}")
                
                # Direct API call to users endpoint
                direct_users = await client.get("http://localhost:8080/api/users")
                print(f"   Direct /api/users: {direct_users.json()}")
        except Exception as e:
            print(f"   Error with direct calls: {e}")

async def main():
    client = MCPClientSimulator()
    await client.simulate_ai_workflow()

if __name__ == "__main__":
    asyncio.run(main()) 