import asyncio
import os
import sys
from typing import Optional
from contextlib import AsyncExitStack

from dotenv import load_dotenv

# MCP imports for stdio communication
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Import our custom GPT utility class
from gpt_utils import GptCall

class MCPStdioClient:
    """
    An MCP client that connects to an MCP server using stdio communication
    and processes queries using Azure OpenAI via the GptCall utility and the server's tools.
    """
    
    def __init__(self):
        # Load environment variables from .env file first
        load_dotenv()
        
        # Initialize GPT client using our custom class
        self.gpt_client = GptCall(gpt_version='gpt4')
        
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
            
            # Determine server type (Python or Node.js)
            is_python = server_script_path.endswith('.py')
            is_js = server_script_path.endswith('.js')
            if not (is_python or is_js):
                print("Error: Server script must be a .py or .js file")
                return False

            # Configure server parameters based on whether we're using uv or not
            env = os.environ.copy()  # Use environment with variables loaded from .env
            
            if use_uv and is_python and server_dir:
                # Using uv to run the server from specified directory
                print(f"Using uv to run server from directory: {server_dir}")
                command = "uv"
                script_name = os.path.basename(server_script_path)
                args = ["--directory", server_dir, "run", script_name]
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
        Process a query using OpenAI and the MCP server's tools
        
        Args:
            query: The user's question or request
            
        Returns:
            OpenAI's response as a string
        """
        if not self.session:
            return "Error: Not connected to an MCP server"
            
        try:
            # Prepare initial chat messages
            messages = [
                {"role": "system", "content": "You are a helpful assistant that helps users with queries"},
                {"role": "user", "content": query}
            ]

            # Convert MCP tools to OpenAI tool format for context
            available_tools = [{
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema
                }
            } for tool in self.tools]

            # Create system message with available tools information
            tools_info = "\n".join([f"- {tool.name}: {tool.description}" for tool in self.tools])
            system_message = f"""You are a helpful assistant that helps users with queries. 
You have access to the following tools:
{tools_info}

If you need to use any of these tools to answer the user's question, please specify which tool you want to use and what parameters you need."""

            # Initial call to our GPT client
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": query}
            ]

            print("Sending query to GPT...")
            response_content = self.gpt_client.call_gpt(messages)

            # Process response and handle potential tool usage
            final_text = [response_content]
            
            # Simple tool detection - look for tool names in the response
            # This is a simplified approach since we're not using native tool calling
            tool_used = False
            for tool in self.tools:
                if tool.name.lower() in response_content.lower():
                    try:
                        # For now, try calling the tool with empty parameters
                        # In a more sophisticated implementation, you'd parse parameters from the response
                        print(f"Attempting to call tool: {tool.name}")
                        result = await self.session.call_tool(tool.name, {})
                        tool_result = result.content
                        final_text.append(f"\n[Tool: {tool.name}]\n{tool_result}")
                        
                        # Get final response with tool results
                        messages.append({"role": "assistant", "content": response_content})
                        messages.append({"role": "user", "content": f"Here's the result from {tool.name}: {tool_result}. Please provide a final answer based on this information."})
                        
                        print("Getting final response with tool results...")
                        final_response = self.gpt_client.call_gpt(messages)
                        final_text.append(f"\n{final_response}")
                        tool_used = True
                        break
                        
                    except Exception as e:
                        error_msg = f"Error calling tool {tool.name}: {str(e)}"
                        print(error_msg)
                        final_text.append(f"\n[Error with tool {tool.name}]: {str(e)}")

            return "\n".join([text for text in final_text if text])
            
        except Exception as e:
            print(f"Error processing query: {str(e)}")
            import traceback
            traceback.print_exc()
            return f"Error processing query: {str(e)}"

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Stdio Client Started! Let's start chatting.")

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
        print("Usage: uv run client.py <path_to_mcp_server_script> [--use-uv] [--server-dir=DIR]")
        return
    
    server_script = sys.argv[1]
    
    # Parse additional command line arguments
    use_uv = "--use-uv" in sys.argv
    server_dir = None
    
    for arg in sys.argv:
        if arg.startswith("--server-dir="):
            server_dir = arg.split("=", 1)[1]
    
    # If using uv but no server directory specified, extract from server script path
    if use_uv and not server_dir:
        server_dir = os.path.dirname(server_script)
        if not server_dir:
            server_dir = "."
    
    # Initialize and run client
    client = MCPStdioClient()
    
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