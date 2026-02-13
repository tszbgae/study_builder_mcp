import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import ollama

# Configuration
OLLAMA_MODEL = "qwen38B_analyst:latest"
SERVER_SCRIPT = "server.py" 

async def run():
    # Connect to the MCP Server we just wrote
    server_params = StdioServerParameters(
        command="fastmcp",
        args=["run", SERVER_SCRIPT],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 1. Initialize tools
            await session.initialize()
            
            # 2. List available tools
            tools = await session.list_tools()
            tool_definitions = []
            
            # Convert MCP tool format to Ollama tool format
            for tool in tools.tools:
                tool_definitions.append({
                    'type': 'function',
                    'function': {
                        'name': tool.name,
                        'description': tool.description,
                        'parameters': tool.inputSchema
                    }
                })

            print("Connected to MCP Server. Type 'quit' to exit.")
            
            messages = []
            
            while True:
                user_input = input("\nYou: ")
                if user_input.lower() in ['quit', 'exit']:
                    break
                    
                messages.append({'role': 'user', 'content': user_input})
                
                # Call Ollama with the tools
                response = ollama.chat(
                    model=OLLAMA_MODEL, # Make sure you have a tool-capable model
                    messages=messages,
                    tools=tool_definitions,
                )
                
                # Check if the model wants to call a tool
                if response.message.tool_calls:
                    for tool_call in response.message.tool_calls:
                        fn_name = tool_call.function.name
                        fn_args = tool_call.function.arguments
                        
                        print(f"[Tool Call] {fn_name}({fn_args})")
                        
                        # Execute the tool via MCP
                        result = await session.call_tool(fn_name, fn_args)
                        
                        # Feed the result back to Ollama
                        messages.append(response.message)
                        messages.append({
                            'role': 'tool',
                            'content': str(result.content),
                        })
                    
                    # Get final response from Ollama after tool execution
                    final_response = ollama.chat(model=OLLAMA_MODEL, messages=messages)
                    print(f"AI: {final_response.message.content}")
                    messages.append(final_response.message)
                
                else:
                    print(f"AI: {response.message.content}")
                    messages.append(response.message)

if __name__ == "__main__":
    asyncio.run(run())