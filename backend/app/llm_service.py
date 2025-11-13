"""
LLM Service - Integration with Ollama and MCP tools
"""
import json
import ollama
from typing import List, Dict, Any, Optional, AsyncGenerator
from .config import settings
from .models import ChatMessage
from .mcp_server import mcp_server


class LLMService:
    """Service for handling LLM interactions with MCP tool integration"""

    def __init__(self):
        self.model = settings.OLLAMA_MODEL
        self.base_url = settings.OLLAMA_BASE_URL
        # Initialize Ollama client with custom host
        self.client = ollama.Client(host=self.base_url)
        self.mcp_tools = self._get_mcp_tools()

    def _get_mcp_tools(self) -> List[Dict[str, Any]]:
        """
        Convert MCP server tools to Ollama function calling format
        """
        tools = []

        # Get all registered tools from MCP server (FastMCP 2.x API)
        # In FastMCP 2.x, tools are stored in _tool_manager._tools
        mcp_tools_dict = {}
        if hasattr(mcp_server, '_tool_manager') and hasattr(mcp_server._tool_manager, '_tools'):
            # _tools is a dict of tool name -> Tool object
            # Each Tool object has a 'fn' attribute with the actual function
            mcp_tools_dict = {name: tool.fn for name, tool in mcp_server._tool_manager._tools.items()}

        for tool_name, tool_func in mcp_tools_dict.items():
            # Get function signature and docstring
            import inspect

            sig = inspect.signature(tool_func)
            doc = inspect.getdoc(tool_func) or ""

            # Build parameters schema
            parameters = {
                "type": "object",
                "properties": {},
                "required": []
            }

            for param_name, param in sig.parameters.items():
                param_type = "string"  # Default type
                if param.annotation != inspect.Parameter.empty:
                    # Map Python types to JSON schema types
                    if param.annotation == int:
                        param_type = "integer"
                    elif param.annotation == float:
                        param_type = "number"
                    elif param.annotation == bool:
                        param_type = "boolean"
                    elif param.annotation == list or str(param.annotation).startswith("List"):
                        param_type = "array"
                    elif param.annotation == dict or str(param.annotation).startswith("Dict"):
                        param_type = "object"

                parameters["properties"][param_name] = {
                    "type": param_type,
                    "description": f"Parameter: {param_name}"
                }

                # Mark as required if no default value
                if param.default == inspect.Parameter.empty:
                    parameters["required"].append(param_name)

            tool_schema = {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": doc.split('\n')[0] if doc else tool_name,
                    "parameters": parameters
                }
            }

            tools.append(tool_schema)

        return tools

    async def chat(
        self,
        message: str,
        conversation_history: List[ChatMessage],
        file_path: Optional[str] = None,
        stream: bool = False
    ) -> AsyncGenerator[str, None]:
        """
        Process chat message with LLM and MCP tools

        Args:
            message: User message
            conversation_history: Previous conversation messages
            file_path: Path to uploaded Excel file (for context)
            stream: Whether to stream the response

        Yields or Returns:
            Assistant response (streamed or complete)
        """
        # Build messages for Ollama
        messages = []

        # System message with context about available tools
        system_msg = (
            "You are an expert Excel data analyst with access to powerful MCP tools.\n\n"
            "CRITICAL RULES:\n"
            "1. ALWAYS use tools to explore and analyze data - NEVER make assumptions\n"
            "2. When asked about data, FIRST use get_workbook_metadata to see sheet names\n"
            "3. Then use read_data_from_excel or analyze_excel_data to examine the actual data\n"
            "4. Be thorough - check column names, data types, and sample rows before answering\n"
            "5. If searching for specific values, use the tools to filter and search the data\n\n"
        )

        if file_path:
            system_msg += f"Excel file location: {file_path}\n"
            system_msg += (
                "WORKFLOW: First explore file structure → Then analyze specific data → "
                "Finally provide accurate answers based on actual tool results.\n"
            )

        messages.append({
            "role": "system",
            "content": system_msg
        })

        # Add conversation history
        for msg in conversation_history:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })

        # Add current user message
        messages.append({
            "role": "user",
            "content": message
        })

        # Call Ollama with function calling
        response = self.client.chat(
            model=self.model,
            messages=messages,
            tools=self.mcp_tools,
            stream=stream
        )

        if stream:
            # Stream response
            async for chunk in self._handle_streaming_response(response):
                yield chunk
        else:
            # Handle complete response with progress updates
            async for chunk in self._handle_response(response, messages):
                yield chunk

    async def _handle_response(
        self,
        response: Dict[str, Any],
        messages: List[Dict[str, Any]]
    ) -> AsyncGenerator[str, None]:
        """
        Handle LLM response including tool calls, yielding progress updates

        Args:
            response: Ollama response
            messages: Current message history

        Yields:
            Progress updates and final assistant response
        """
        assistant_message = response.get('message', {})

        # Check if there are tool calls
        tool_calls = assistant_message.get('tool_calls', [])

        if not tool_calls:
            # No tool calls, return direct response
            yield assistant_message.get('content', '')
            return

        # Execute tool calls with progress updates
        messages.append(assistant_message)

        for idx, tool_call in enumerate(tool_calls, 1):
            function_name = tool_call['function']['name']
            function_args = tool_call['function']['arguments']

            # Yield progress update
            yield f"\n🔧 [Tool {idx}/{len(tool_calls)}] Executing: {function_name}...\n"

            # Execute MCP tool
            try:
                result = await self._execute_mcp_tool(function_name, function_args)

                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "content": json.dumps(result),
                    "name": function_name
                })

                # Yield completion update
                yield f"✓ [Tool {idx}/{len(tool_calls)}] Completed: {function_name}\n"

            except Exception as e:
                # Handle tool execution errors
                messages.append({
                    "role": "tool",
                    "content": json.dumps({"error": str(e)}),
                    "name": function_name
                })

                # Yield error update
                yield f"✗ [Tool {idx}/{len(tool_calls)}] Failed: {function_name} - {str(e)}\n"

        # Yield final analysis message
        yield "\n💭 Analyzing results...\n\n"

        # Get final response from LLM after tool execution
        final_response = self.client.chat(
            model=self.model,
            messages=messages
        )

        yield final_response['message']['content']

    async def _handle_streaming_response(
        self,
        response_stream
    ) -> AsyncGenerator[str, None]:
        """
        Handle streaming LLM response with tool calls

        Args:
            response_stream: Ollama streaming response

        Yields:
            Response chunks
        """
        for chunk in response_stream:
            message = chunk.get('message', {})
            content = message.get('content', '')

            if content:
                yield content

            # Note: Tool calling in streaming mode is more complex
            # For now, we'll handle it in non-streaming mode
            # Production implementation would need proper streaming + tools handling

    async def _execute_mcp_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Any:
        """
        Execute MCP tool by name

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        tools = mcp_server.list_tools()

        if tool_name not in tools:
            raise ValueError(f"Tool '{tool_name}' not found")

        tool_func = tools[tool_name]

        # Execute tool
        result = tool_func(**arguments)

        return result

    def check_ollama_status(self) -> Dict[str, Any]:
        """
        Check if Ollama is running and model is available

        Returns:
            Status information
        """
        try:
            models_response = self.client.list()
            # In ollama library, models is an attribute, and each model has a 'model' attribute
            model_list = models_response.models if hasattr(models_response, 'models') else []
            model_names = [m.model for m in model_list]

            is_model_available = any(
                self.model in name for name in model_names
            )

            return {
                'status': 'running',
                'model': self.model,
                'model_available': is_model_available,
                'available_models': model_names
            }
        except Exception as e:
            import traceback
            return {
                'status': 'error',
                'error': f"Error: {str(e)}",
                'traceback': traceback.format_exc(),
                'model': self.model,
                'model_available': False
            }

    async def pull_model_if_needed(self):
        """
        Pull the model from Ollama if not available
        """
        status = self.check_ollama_status()

        if not status.get('model_available', False):
            try:
                self.client.pull(self.model)
                return {'success': True, 'message': f'Model {self.model} pulled successfully'}
            except Exception as e:
                return {'success': False, 'error': str(e)}

        return {'success': True, 'message': 'Model already available'}


# Singleton instance
llm_service = LLMService()
