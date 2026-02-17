import asyncio
import json
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from llama_cpp import Llama

# --- Configuration ---
SERVER_SCRIPT = "server.py"
MODEL_PATH = "../ggufs/Qwen3-8B-Q5_K_M.gguf"  # <--- UPDATE THIS PATH
CONTEXT_SIZE = 8192

def run_llama_inference(llm, messages, tools):
    """
    Helper to run inference with tool support.
    """
    # Llama-cpp-python's create_chat_completion supports the 'tools' parameter directly
    response = llm.create_chat_completion(
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=0.1, 
        top_p=0.9,
    )
    return response

async def run():
    # 1. Start the MCP Server
    server_params = StdioServerParameters(
        command=sys.executable,  # Use the same python executable
        args=[SERVER_SCRIPT],
    )

    print(f"Loading model from {MODEL_PATH}...")
    try:
        # Initialize Llama model
        llm = Llama(
            model_path=MODEL_PATH,
            n_ctx=CONTEXT_SIZE,
            n_gpu_layers=-1,
            verbose=False # Set to True to see speed stats
        )
    except Exception as e:
        print(f"Error loading model: {e}")
        return

    print("Connecting to MCP Server...")
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # 2. Get Tools from MCP
            mcp_list = await session.list_tools()
            
            # Convert MCP tools to OpenAI/Llama-cpp format
            llama_tools = []
            for tool in mcp_list.tools:
                llama_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema
                    }
                })
            
            print(f"\nLoaded {len(llama_tools)} tools. Ready to chat! (Type 'quit' to exit)")

            # 3. Chat Loop
            messages = [
                {"role": "system", 
                 "content": """ 
                 You are helpful and polite assistant, helping the user create the necessary parts of a study json to then convert to python and execute in a study.  

YOUR GOAL:
Help the user compose the study json by ensuring the following pieces of information are added: an executable file, inputs, and outputs. When all this required information is loaded into the {study name}.json, the next step is to build the python study file.  Once the study file is built, execute the study.  at any time after, the user may inquire on the progress of the study.  

YOUR TOOLKIT (MCP):
You have access to a server that manages the state of building the json, building the study file, executing and getting progress of execution.
1. create_or_load_study - initiate the study json and save.  A study name is required as input, saved in the json and is the name of the json.  
2. set_executable_path - sets the executable path in the json. 
3. Adding input - can be done manually in plain text to you with add_input_manual (name, lower and upper bound needed) or add_inputs_from_csv...for this you need the path to the csv.  A function will open the csv, get the information and load into the study json. 
4. read_available_outputs_from_file - the user will point to a text file containing output names.  user will select at least one of these values, after which you will run set_study_outputs to place the outputs in the study json. 
5. get_study_status - if the user requests the status of the study json, this function will help you to provide the status of valid executable, inputs and outputs
6. build_studypy_from_json - if the json is valid, this function builds the json into an executable python study file
7. run_study_script - runs the python study file created in build_studypy_from_json
8. get_study_progress - get the progress of the study from the output csv file created in study execution.  

OPERATIONAL RULES:
1.  An executable path is required.  At least one input (with name, lower and upper bound) is required.  At least one output is required and the outputs must match what is in proved from the read_available_outputs_from_file function. If this information is not in the json, do not proceed with creating the python study file
"""
                 }
            ]

            while True:
                user_input = input("\nYou: ")
                if user_input.lower() in ["quit", "exit"]:
                    break
                
                messages.append({"role": "user", "content": user_input})
                
                # First Pass: Check for tool calls
                response = run_llama_inference(llm, messages, llama_tools)
                response_message = response["choices"][0]["message"]
                
                # Check if the model wants to call tools
                tool_calls = response_message.get("tool_calls")
                
                if tool_calls:
                    # Append the model's "intent" to call a tool to history
                    messages.append(response_message)
                    
                    print("\n[Processing Tool Calls...]")
                    
                    for tool_call in tool_calls:
                        fn_name = tool_call["function"]["name"]
                        fn_args_str = tool_call["function"]["arguments"]
                        fn_args = json.loads(fn_args_str)
                        
                        print(f" > Calling: {fn_name}({fn_args_str})")
                        
                        # Execute Tool via MCP
                        try:
                            result = await session.call_tool(fn_name, fn_args)
                            tool_output = str(result.content)
                        except Exception as e:
                            tool_output = f"Error executing tool: {e}"
                            
                        print(f" < Result: {tool_output[:100]}...") # Truncate log for readability

                        # Append result to history
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": tool_output
                        })
                    
                    # Second Pass: Get final response with tool outputs
                    final_response = run_llama_inference(llm, messages, llama_tools)
                    final_content = final_response["choices"][0]["message"]["content"]
                    
                    print(f"\nAI: {final_content}")
                    messages.append({"role": "assistant", "content": final_content})
                    
                else:
                    # No tool called, just normal chat
                    content = response_message["content"]
                    print(f"\nAI: {content}")
                    messages.append({"role": "assistant", "content": content})

if __name__ == "__main__":
    asyncio.run(run())