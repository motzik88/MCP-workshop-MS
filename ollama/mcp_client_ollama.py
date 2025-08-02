import asyncio
import os
import sys
from typing import Optional
from contextlib import AsyncExitStack

from dotenv import load_dotenv

# MCP imports for stdio communication
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Import our custom Ollama utility class
from ollama_utils import OllamaCall

class MCPOllamaClient:
    """
    An MCP client that connects to an MCP server using stdio communication
    and processes queries using Ollama local models and the server's tools.
    """
    
    def __init__(self, model_name: str = "llama3.2:3b"):
        # Load environment variables from .env file first
        load_dotenv()
        
        # Initialize Ollama client using our custom class
        self.ollama_client = OllamaCall(model_name=model_name)
        
        # Test Ollama connection
        print(f"Testing connection to Ollama with model: {model_name}")
        if not self.ollama_client.test_connection():
            print("Warning: Could not connect to Ollama. Make sure:")
            print("1. Ollama is installed")
            print("2. Ollama server is running (ollama serve)")
            print(f"3. Model '{model_name}' is available (ollama pull {model_name})")
            available_models = self.ollama_client.list_models()
            if available_models:
                print(f"Available models: {available_models}")
        else:
            print("✓ Successfully connected to Ollama")
        
        # Initialize session and stdio objects
        self.session: Optional[ClientSession] = None
        self.stdio = None
        self.write = None
        self.exit_stack = AsyncExitStack()
        
        # Store server tools
        self.tools = []

    async def connect_to_server(self, server_script_path: str, use_uv: bool = False, server_dir: str = None) -> bool:
        """
        Connect to an MCP server via stdio
        
        Args:
            server_script_path: Path to the server script (.py or .js)
            use_uv: Whether to use uv to run the server
            server_dir: Directory to run uv from
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            print(f"Connecting to MCP server at: {server_script_path}")
            
            # Configure server parameters based on whether we're using uv or not
            env = os.environ.copy()  # Use environment with variables loaded from .env
            
            # When using uv, we don't need file extension validation as it's a package name
            if use_uv and server_dir:
                # Using uv package - no file extension required
                is_python = True  # Assume Python for uv packages
                is_js = False
            else:
                # Determine server type (Python or Node.js) for direct script execution
                is_python = server_script_path.endswith('.py')
                is_js = server_script_path.endswith('.js')
                if not (is_python or is_js):
                    print("Error: Server script must be a .py or .js file")
                    return False
            
            if use_uv and is_python and server_dir:
                # Using uv to run the server from specified directory
                print(f"Using uv to run server from directory: {server_dir}")
                command = "uv"
                # For uv packages, use the server_script_path as the package name directly
                package_name = server_script_path
                args = ["--directory", server_dir, "run", package_name]
            else:
                # Using default Python or Node interpreter
                command = "python" if is_python else "node"
                args = [server_script_path]

            server_params = StdioServerParameters(
                command=command,
                args=args,
                env=env
            )

            # Connect to server
            stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
            self.stdio, self.write = stdio_transport
            self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

            # Initialize session
            print("Initializing MCP session...")
            await self.session.initialize()

            # Fetch available tools
            response = await self.session.list_tools()
            self.tools = response.tools
            
            if self.tools:
                print(f"\nConnected to server with {len(self.tools)} tools:")
                for tool in self.tools:
                    print(f"  - {tool.name}: {tool.description}")
            else:
                print("Connected to server but no tools available")
                
            return True
            
        except Exception as e:
            print(f"Error connecting to MCP server: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    async def process_query(self, query: str) -> str:
        """
        Process a query using Ollama and the MCP server's tools
        
        Args:
            query: The user's question or request
            
        Returns:
            Ollama's response as a string
        """
        if not self.session:
            return "Error: Not connected to an MCP server"
            
        try:
            # Create system message with available tools information
            tools_info = "\n".join([f"- {tool.name}: {tool.description}" for tool in self.tools])
            system_message = f"""You are a helpful assistant that helps users with queries. 
You have access to the following tools:
{tools_info}

If you need to use any of these tools to answer the user's question, please respond with:
TOOL_REQUEST: <tool_name>
PARAMETERS: <describe what parameters you need>

Otherwise, provide a direct answer to the user's question."""

            # Initial call to Ollama
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": query}
            ]

            print("Sending query to Ollama...")
            response_content = self.ollama_client.call_ollama(messages)

            # Process response and handle potential tool usage
            final_text = [response_content]
            
            # Check if Ollama wants to use a tool
            if "TOOL_REQUEST:" in response_content:
                lines = response_content.split('\n')
                tool_name = None
                parameters = {}
                
                for line in lines:
                    if line.strip().startswith("TOOL_REQUEST:"):
                        tool_name = line.replace("TOOL_REQUEST:", "").strip()
                    elif line.strip().startswith("PARAMETERS:"):
                        params_str = line.replace("PARAMETERS:", "").strip()
                        # Parse the parameters from the response
                        # Example: "principal=5000, annual_rate=0.06, compounds_per_year=12, years=13"
                        try:
                            import re
                            # Extract key=value pairs
                            param_matches = re.findall(r'(\w+)=([^,]+)', params_str)
                            for key, value in param_matches:
                                # Try to convert to appropriate type
                                value = value.strip()
                                try:
                                    # Try int first
                                    if '.' not in value:
                                        parameters[key] = int(value)
                                    else:
                                        parameters[key] = float(value)
                                except ValueError:
                                    # Keep as string if not a number
                                    parameters[key] = value
                        except Exception as e:
                            print(f"Warning: Could not parse parameters: {e}")
                            parameters = {}
                
                if tool_name:
                    # Find the tool
                    tool_to_use = None
                    for tool in self.tools:
                        if tool.name.lower() == tool_name.lower():
                            tool_to_use = tool
                            break
                    
                    if tool_to_use:
                        try:
                            print(f"Calling tool: {tool_to_use.name} with parameters: {parameters}")
                            result = await self.session.call_tool(tool_to_use.name, parameters)
                            tool_result = result.content
                            final_text.append(f"\n[Tool: {tool_to_use.name}]\n{tool_result}")
                            
                            # Get final response with tool results
                            messages.append({"role": "assistant", "content": response_content})
                            messages.append({"role": "user", "content": f"Here's the result from {tool_to_use.name}: {tool_result}. Please provide a final answer based on this information."})
                            
                            print("Getting final response with tool results...")
                            final_response = self.ollama_client.call_ollama(messages)
                            final_text.append(f"\n{final_response}")
                            
                        except Exception as e:
                            error_msg = f"Error calling tool {tool_to_use.name}: {str(e)}"
                            print(error_msg)
                            final_text.append(f"\n[Error with tool {tool_to_use.name}]: {str(e)}")

            return "\n".join([text for text in final_text if text])
            
        except Exception as e:
            print(f"Error processing query: {str(e)}")
            import traceback
            traceback.print_exc()
            return f"Error processing query: {str(e)}"

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print(f"\nMCP Ollama Client Started with model: {self.ollama_client.model_name}")
        print("Let's start chatting!")

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() in ('quit', 'exit'):
                    break

                response = await self.process_query(query)
                print("\nResponse:")
                print(response)

            except Exception as e:
                print(f"\nError: {str(e)}")
                import traceback
                traceback.print_exc()

    async def cleanup(self):
        """Clean up resources"""
        if self.session:
            await self.exit_stack.aclose()
            print("Connection to MCP server closed")


async def main():
    # Validate command line arguments
    if len(sys.argv) < 2:
        print("Usage: uv run mcp_client_ollama.py <path_to_mcp_server_script> [--model=MODEL_NAME] [--use-uv] [--server-dir=DIR]")
        print("Example: uv run mcp_client_ollama.py server.py --model=llama3.2:8b")
        return
    
    server_script = sys.argv[1]
    
    # Parse additional command line arguments
    use_uv = "--use-uv" in sys.argv
    server_dir = None
    model_name = "llama3.2:3b"  # Default model
    
    for arg in sys.argv:
        if arg.startswith("--server-dir="):
            server_dir = arg.split("=", 1)[1]
        elif arg.startswith("--model="):
            model_name = arg.split("=", 1)[1]
    
    # If using uv but no server directory specified, extract from server script path
    if use_uv and not server_dir:
        server_dir = os.path.dirname(server_script)
        if not server_dir:
            server_dir = "."
    
    # Initialize and run client
    client = MCPOllamaClient(model_name=model_name)
    
    try:
        # Connect to server
        if await client.connect_to_server(server_script, use_uv, server_dir):
            # Start interactive chat loop
            await client.chat_loop()
    finally:
        # Clean up resources
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())