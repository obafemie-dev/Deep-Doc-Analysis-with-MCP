"""
Claude LLM Service - Single-turn integration with Anthropic Claude and MCP tools
"""
import json
import logging
import os
from anthropic import Anthropic
from typing import List, Dict, Any, Optional, AsyncGenerator
from .config import settings
from .schemas import ChatMessage
from .mcp_server import mcp_server
from .mcp_server.utils import coerce_string_to_type

logger = logging.getLogger(__name__)


# Tools that modify the spreadsheet and should trigger viewer refresh
SHEET_MODIFYING_TOOLS = {
    'create_chart',
    'create_pivot_table',
    'create_dashboard',
    'create_table',
    'write_data_to_excel',
    'apply_formula',
    'format_range',
    'insert_rows',
    'insert_columns',
    'delete_rows',
    'delete_columns',
    'create_worksheet',
    'delete_worksheet',
    'rename_worksheet',
    'copy_worksheet'
}


class ClaudeLLMService:
    """Service for handling LLM interactions with Claude and MCP tool integration"""

    def __init__(self):
        self.model = settings.CLAUDE_MODEL
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.mcp_tools = self._get_mcp_tools()
        self.max_context_tokens = 150000  # Leave 50k for response

    def _get_mcp_tools(self) -> List[Dict[str, Any]]:
        """
        Convert MCP server tools to Claude tool format
        """
        tools = []

        # Get all registered tools from MCP server
        mcp_tools_dict = {}
        if hasattr(mcp_server, '_tool_manager') and hasattr(mcp_server._tool_manager, '_tools'):
            mcp_tools_dict = {name: tool.fn for name, tool in mcp_server._tool_manager._tools.items()}

        for tool_name, tool_func in mcp_tools_dict.items():
            # Get function signature and docstring
            import inspect

            sig = inspect.signature(tool_func)
            doc = inspect.getdoc(tool_func) or ""

            # Build parameters schema for Claude
            properties = {}
            required = []

            for param_name, param in sig.parameters.items():
                param_type = "string"  # Default type
                param_desc = f"Parameter: {param_name}"

                if param.annotation != inspect.Parameter.empty:
                    # Convert annotation to string for checking
                    annotation_str = str(param.annotation)

                    # Map Python types to JSON schema types
                    if param.annotation == int or 'int' in annotation_str:
                        param_type = "integer"
                    elif param.annotation == float or 'float' in annotation_str:
                        param_type = "number"
                    elif param.annotation == bool or 'bool' in annotation_str:
                        param_type = "boolean"
                    elif param.annotation == list or 'List[' in annotation_str or annotation_str.startswith('list'):
                        param_type = "array"
                    elif param.annotation == dict or 'Dict[' in annotation_str or annotation_str.startswith('dict'):
                        param_type = "object"
                        # Add description for dict parameters
                        if 'filters' in param_name.lower():
                            param_desc = "Dictionary of column filters, e.g. {'Model': '4430'}"

                    # For array types, add items description
                    if param_type == "array" and 'columns' in param_name.lower():
                        param_desc = "List of column names to return"

                properties[param_name] = {
                    "type": param_type,
                    "description": param_desc
                }

                # Mark as required if no default value
                if param.default == inspect.Parameter.empty:
                    required.append(param_name)

            tool_schema = {
                "name": tool_name,
                "description": doc.split('\n')[0] if doc else tool_name,
                "input_schema": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }

            tools.append(tool_schema)

        return tools

    def _estimate_tokens(self, content: Any) -> int:
        """
        Rough token estimation (1 token ≈ 3.5 chars for better accuracy)

        Args:
            content: String, list, dict, or Claude content blocks

        Returns:
            Estimated token count
        """
        if isinstance(content, str):
            # Use 3.5 chars per token for better accuracy
            return len(content) * 10 // 35
        elif isinstance(content, list):
            # Could be a list of Claude content blocks or regular list
            total_chars = 0
            for item in content:
                # Check if it's a Claude block object with attributes
                if hasattr(item, 'type'):
                    # It's a Claude block (TextBlock, ToolUseBlock, etc.)
                    # Try model_dump() first (Pydantic v2)
                    if hasattr(item, 'model_dump'):
                        try:
                            item_dict = item.model_dump()
                            total_chars += len(json.dumps(item_dict))
                            continue
                        except Exception:
                            pass

                    # Fallback to type-specific handling
                    if item.type == 'text' and hasattr(item, 'text'):
                        total_chars += len(item.text)
                    elif item.type == 'tool_use':
                        # Estimate tool_use block size (~500 chars typically)
                        total_chars += 500
                    elif item.type == 'tool_result':
                        # Estimate based on content if available
                        if hasattr(item, 'content'):
                            total_chars += len(str(item.content))
                        else:
                            total_chars += 200
                    else:
                        # Unknown block type, use string representation
                        total_chars += len(str(item))
                else:
                    # Regular dict/object, try to serialize
                    try:
                        total_chars += len(json.dumps(item))
                    except (TypeError, ValueError):
                        total_chars += len(str(item))
            return total_chars * 10 // 35
        elif isinstance(content, dict):
            # Try to serialize dict
            try:
                json_str = json.dumps(content)
                return len(json_str) * 10 // 35
            except (TypeError, ValueError):
                # If JSON serialization fails, use string representation
                return len(str(content)) * 10 // 35
        else:
            # Check if it's a Claude object with model_dump
            if hasattr(content, 'model_dump'):
                try:
                    content_dict = content.model_dump()
                    return len(json.dumps(content_dict)) * 10 // 35
                except Exception:
                    pass
            # Fallback for other types
            return len(str(content)) * 10 // 35

    def _truncate_large_result(self, result: Any, max_chars: int = 10000) -> Any:
        """
        Truncate large tool results to prevent token overflow

        Args:
            result: Tool execution result
            max_chars: Maximum characters allowed (~5k tokens)

        Returns:
            Truncated result if needed
        """
        if not isinstance(result, dict):
            return result

        result_str = json.dumps(result)

        # If result is small enough, return as-is
        if len(result_str) <= max_chars:
            return result

        # Check if this is a data-heavy result (from read_data_from_excel or similar)
        if "data" in result and isinstance(result["data"], list):
            data_list = result["data"]
            return {
                "summary": f"Data retrieved successfully (showing sample of {len(data_list)} total rows)",
                "row_count": len(data_list),
                "columns": list(data_list[0].keys()) if data_list else [],
                "sample_rows": data_list[:10],  # First 10 rows
                "last_rows": data_list[-3:] if len(data_list) > 13 else [],  # Last 3 rows
                "note": "Full dataset truncated to prevent context overflow. Ask specific questions about the data."
            }

        # For other large dictionaries, try to summarize intelligently
        truncated = {}
        for key, value in result.items():
            if isinstance(value, (list, dict)):
                value_str = json.dumps(value)
                if len(value_str) > 1000:
                    if isinstance(value, list):
                        truncated[key] = {
                            "type": "list",
                            "length": len(value),
                            "sample": value[:3] if value else []
                        }
                    else:
                        truncated[key] = {"type": "dict", "keys": list(value.keys())[:10]}
                else:
                    truncated[key] = value
            else:
                truncated[key] = value

        return truncated

    def _build_messages(
        self,
        conversation_history: List[ChatMessage],
        message: str,
        file_path: Optional[str] = None
    ) -> tuple[List[Dict[str, Any]], str]:
        """
        Build messages with token-aware truncation

        Returns:
            Tuple of (messages list, system prompt)
        """
        messages = []
        total_tokens = 0

        # Build system prompt
        system_prompt = (
            "You are an expert Excel data analyst with access to powerful MCP tools.\n\n"
            "CRITICAL RESPONSE RULES:\n"
            "1. Use the MINIMUM number of tool calls (ideally 1-2 calls total)\n"
            "2. Call tools WITHOUT any explanatory text\n"
            "3. After receiving tool results, provide your FINAL ANSWER immediately - do NOT make more tool calls\n"
            "4. Your final answer must contain ONLY text (no tool calls)\n"
            "5. Workflow: [1-2 tool calls] → [Final text answer]\n\n"
            "CRITICAL TOOL SELECTION:\n"
            "1. For data queries: use query_excel_data with filters (queries FULL dataset)\n"
            "2. For statistics: use analyze_excel_data (returns mean, std, etc)\n"
            "3. NEVER use read_data_from_excel for queries (truncated samples only)\n"
            "4. Example filters: {'Model': '4430'} or {'Year': 2023}\n\n"
            "COLUMN NAMES - CRITICAL:\n"
            "1. ALWAYS get exact column names from get_workbook_metadata FIRST\n"
            "2. Use EXACT column names from metadata - DO NOT guess or modify them\n"
            "3. get_workbook_metadata returns 'column_names' array for each sheet\n"
            "4. NEVER add words like 'Price' if not in actual column name\n\n"
            "OPTIMAL WORKFLOW (2 tool calls max):\n"
            "1. Call get_workbook_metadata to discover column names\n"
            "2. Call query_excel_data using EXACT column names from metadata\n"
            "3. Provide final answer with all analysis\n\n"
            "EXAMPLE - CORRECT:\n"
            "User: 'selling vs advertised price for model 4430'\n"
            "You: [Call get_workbook_metadata]\n"
            "Result: sheets_info[0].column_names = ['Model', 'VIN', 'Selling', 'Advertised', ...]\n"
            "You: [Call query_excel_data with filters={'Model': '4430'}, columns=['Selling', 'Advertised']]\n"
            "You: 'Model 4430 has 3 units. Selling: $45k-$50k, Advertised: $48k-$52k...'\n\n"
            "EXAMPLE - WRONG (too many calls):\n"
            "You: [Call get_workbook_metadata] → [Call query_excel_data] → [Call analyze_excel_data] ❌ TOO MANY\n\n"
            "KEY RULES:\n"
            "- Answer immediately after receiving first data results\n"
            "- Do NOT gather additional data unless first results are insufficient\n"
            "- Be decisive - analyze what you have and provide the answer\n\n"
            "CRITICAL ERROR HANDLING RULES:\n"
            "1. NEVER include tool errors in your text response\n"
            "2. Tool errors appear AUTOMATICALLY in the 'Chain of thought' section\n"
            "3. When a tool fails, silently try alternatives - do not explain the failure\n"
            "4. Your text response should ONLY contain the final answer\n"
            "5. FORBIDDEN: Starting responses with 'Error:', mentioning 'not found', or explaining tool failures\n\n"
            "CORRECT BEHAVIOR EXAMPLES:\n"
            "❌ WRONG: 'Error: Column Year not found. Based on the data...'\n"
            "✅ RIGHT: 'Based on the DMB Loans and Advances data, the percentage change is 47.2%'\n\n"
            "If you cannot answer due to tool failures, say: 'I need more information about the column names to answer this question.'\n\n"
        )

        if file_path:
            system_prompt += f"Excel file location: {file_path}\n"

        system_tokens = self._estimate_tokens(system_prompt)
        total_tokens += system_tokens

        # Add current message first (always include)
        current_msg = {"role": "user", "content": message}
        current_tokens = self._estimate_tokens(message)
        messages.append(current_msg)
        total_tokens += current_tokens

        # Add conversation history in reverse (keep most recent)
        for msg in reversed(conversation_history):
            msg_tokens = self._estimate_tokens(msg.content)

            # Stop if we'd exceed context window
            if total_tokens + msg_tokens > self.max_context_tokens:
                break

            messages.insert(0, {"role": msg.role, "content": msg.content})
            total_tokens += msg_tokens

        return messages, system_prompt

    async def chat(
        self,
        message: str,
        conversation_history: List[ChatMessage],
        file_path: Optional[str] = None,
        stream: bool = False,
        session_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Process chat message with Claude and MCP tools (SINGLE TURN)

        Args:
            message: User message
            conversation_history: Previous conversation messages
            file_path: Path to uploaded Excel file (for context)
            stream: Whether to stream the response

        Yields:
            Assistant response with progress updates
        """
        # Build messages with token management
        messages, system_prompt = self._build_messages(conversation_history, message, file_path)

        # Call Claude API (initial call) - no streaming for tool use phase
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_prompt,
            messages=messages,
            tools=self.mcp_tools
        )

        # Handle response with iteration control (max 5 iterations as safety net)
        async for chunk in self._handle_single_turn(
            response,
            messages,
            system_prompt,
            iteration=0,
            max_iterations=5,
            stream=stream,
            session_id=session_id
        ):
            yield chunk

    async def _handle_single_turn(
        self,
        response: Any,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        iteration: int = 0,
        max_iterations: int = 5,
        accumulated_tokens: int = 0,
        stream: bool = False,
        session_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Handle Claude response with controlled iteration loop

        Args:
            response: Claude API response
            messages: Conversation messages
            system_prompt: System instructions
            iteration: Current iteration number (0-indexed)
            max_iterations: Maximum number of iterations allowed
            accumulated_tokens: Total tokens used across iterations
            stream: Whether to use streaming for final response

        This processes the response:
        1. Yields any text content from Claude
        2. Executes any tool calls Claude requested
        3. If iteration < max_iterations, makes another Claude call with tool results
        4. Continues until no more tool calls or max_iterations reached
        """
        # Log iteration start
        logger.info(f"=== Iteration {iteration}/{max_iterations} ===")
        logger.info(f"stop_reason: {response.stop_reason if hasattr(response, 'stop_reason') else 'N/A'}")

        # Safety check: prevent infinite loops
        if iteration >= max_iterations:
            logger.warning(f"Maximum iteration limit ({max_iterations}) reached!")
            # Extract any text from current response to give user SOMETHING
            text_blocks = [block for block in response.content if block.type == "text"]
            if text_blocks:
                logger.info(f"Returning {len(text_blocks)} text block(s) from max iteration response")
                for block in text_blocks:
                    if block.text.strip():
                        yield block.text
            else:
                logger.warning("No text blocks in max iteration response - returning error message")
                yield "\n\n[Maximum iteration limit reached. Try a more specific question or break your query into smaller parts.]"
            return

        # Extract text and tool calls from response
        tool_calls = [block for block in response.content if block.type == "tool_use"]
        text_blocks = [block for block in response.content if block.type == "text"]

        logger.info(f"Response contains: {len(tool_calls)} tool call(s), {len(text_blocks)} text block(s)")

        # If no tool calls, this is the final answer - yield it
        if not tool_calls:
            logger.info("No tool calls - returning final answer")
            for block in text_blocks:
                if block.text.strip():
                    yield block.text
            return

        # If there ARE tool calls, don't yield the "thinking" text
        # (like "Let me check...", "Now let me get...")
        # This text is internal reasoning and should be hidden from user

        # Execute all tool calls (internal reasoning - not shown to user)
        # Add assistant's response to messages
        # NOTE: Must use original response.content format (Claude API expects this)
        # Token management happens via truncation of tool_results instead
        messages.append({
            "role": "assistant",
            "content": response.content
        })

        tool_results = []

        # Log tool calls being made
        logger.info(f"Executing {len(tool_calls)} tool call(s):")
        for tc in tool_calls:
            logger.info(f"  - {tc.name}({list(tc.input.keys()) if hasattr(tc.input, 'keys') else 'no args'})")

        # Notify user that tools are being used (chain of thought)
        if stream and len(tool_calls) > 0:
            tool_names = [tc.name for tc in tool_calls]
            yield {
                "type": "thinking_start",
                "message": f"Using {len(tool_calls)} tool{'s' if len(tool_calls) != 1 else ''} to analyze your data",
                "tools": tool_names
            }

        for idx, tool_call in enumerate(tool_calls, 1):
            function_name = tool_call.name
            function_args = tool_call.input

            # Notify user that tool is starting (chain of thought)
            if stream:
                yield {
                    "type": "tool_start",
                    "tool_name": function_name,
                    "step": idx,
                    "total_steps": len(tool_calls)
                }

            # Execute MCP tool
            try:
                result = await self._execute_mcp_tool(function_name, function_args, session_id)

                # Truncate large results
                result = self._truncate_large_result(result)

                result_size = len(json.dumps(result))
                logger.info(f"Tool '{function_name}' returned result ({result_size} chars)")

                # Notify user of successful completion (chain of thought)
                if stream:
                    summary = self._summarize_tool_result(function_name, result)
                    yield {
                        "type": "tool_complete",
                        "tool_name": function_name,
                        "summary": summary
                    }

                    # Emit sheet_updated event for tools that modify the spreadsheet
                    if function_name in SHEET_MODIFYING_TOOLS:
                        # Extract filename from function args
                        file_path = function_args.get('file_path', '')
                        sheet_name = function_args.get('sheet_name', function_args.get('worksheet_name', ''))

                        # Extract just the filename from the path
                        filename = os.path.basename(file_path) if file_path else ''

                        yield {
                            "type": "sheet_updated",
                            "filename": filename,
                            "sheet_name": sheet_name,
                            "action": function_name
                        }

                # Store for Claude follow-up (internal only)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call.id,
                    "content": json.dumps(result)
                })

            except Exception as e:
                logger.error(f"Tool '{function_name}' failed: {str(e)}")

                # Notify user of error (chain of thought)
                if stream:
                    yield {
                        "type": "tool_error",
                        "tool_name": function_name,
                        "error": str(e)
                    }

                # Log error to analytics
                if settings.ANALYTICS_ENABLED:
                    try:
                        import traceback
                        from .database import AsyncSessionLocal
                        from .services.analytics_service import AnalyticsService

                        async with AsyncSessionLocal() as db:
                            try:
                                analytics = AnalyticsService(db)
                                await analytics.log_error(
                                    session_id=None,  # Session ID not available in claude_service
                                    error_type=type(e).__name__,
                                    error_message=str(e),
                                    stack_trace=traceback.format_exc(),
                                    endpoint=f"tool:{function_name}",
                                    request_data={
                                        "tool_name": function_name,
                                        "tool_params": tool_call.input if hasattr(tool_call, 'input') else {}
                                    }
                                )
                                await db.commit()
                            except Exception:
                                await db.rollback()
                                raise
                            finally:
                                await db.close()
                    except Exception as log_error:
                        logger.error(f"Failed to log tool error to analytics: {log_error}")

                # Store minimal error for Claude (don't reveal details)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call.id,
                    "content": "No results available"
                })

        # If within iteration limit, make another Claude call with tool results
        if iteration < max_iterations and tool_results:
            # Add tool results to messages
            messages.append({
                "role": "user",
                "content": tool_results
            })

            # Estimate current token usage to prevent overflow
            current_tokens = accumulated_tokens
            for msg in messages:
                current_tokens += self._estimate_tokens(msg["content"])
            current_tokens += self._estimate_tokens(system_prompt)

            logger.info(f"Estimated tokens: {current_tokens}/{self.max_context_tokens}")

            # Check if we're approaching token limit (150k)
            if current_tokens > self.max_context_tokens:
                logger.error(f"Token limit exceeded! ({current_tokens} > {self.max_context_tokens})")
                yield "\n\n[Context limit approaching - please use more specific queries or filters]"
                return

            # Notify user that analysis is in progress (chain of thought)
            if stream:
                yield {
                    "type": "thinking",
                    "message": "Analyzing results..."
                }

            logger.info(f"Making follow-up Claude API call (iteration {iteration + 1})")

            # Use streaming when requested (regardless of iteration)
            use_streaming = stream

            if use_streaming:
                logger.info("Using streaming API for final response")
                # Make streaming follow-up call
                follow_up_stream = self.client.messages.stream(
                    model=self.model,
                    max_tokens=4096,
                    system=system_prompt,
                    messages=messages,
                    tools=self.mcp_tools
                )

                # Process streaming response
                with follow_up_stream as stream_manager:
                    # Collect full response for potential recursion
                    full_content = []
                    chunk_count = 0

                    for text in stream_manager.text_stream:
                        chunk_count += 1
                        yield text  # Stream text in real-time
                        full_content.append(text)

                    # Get final message for checking tool calls
                    final_message = stream_manager.get_final_message()

                    # Check if there are tool calls (need to recurse)
                    tool_calls = [block for block in final_message.content if block.type == "tool_use"]

                    if tool_calls:
                        # There are more tool calls - need to recurse
                        async for chunk in self._handle_single_turn(
                            final_message,
                            messages,
                            system_prompt,
                            iteration=iteration + 1,
                            max_iterations=max_iterations,
                            accumulated_tokens=current_tokens,
                            stream=stream,  # Preserve streaming for final response
                            session_id=session_id
                        ):
                            yield chunk
            else:
                # Make non-streaming follow-up call (for tool execution phase)
                follow_up_response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=system_prompt,
                    messages=messages,
                    tools=self.mcp_tools
                )

                # Handle follow-up with incremented iteration counter AND token tracking
                async for chunk in self._handle_single_turn(
                    follow_up_response,
                    messages,
                    system_prompt,
                    iteration=iteration + 1,  # Increment iteration
                    max_iterations=max_iterations,
                    accumulated_tokens=current_tokens,  # Pass tokens forward
                    stream=stream,  # Pass streaming flag
                    session_id=session_id
                ):
                    yield chunk

    def _summarize_tool_result(self, tool_name: str, result: Any) -> str:
        """
        Create user-friendly summary of tool execution result

        Args:
            tool_name: Name of the tool executed
            result: Tool execution result

        Returns:
            User-friendly summary string
        """
        try:
            if isinstance(result, dict):
                # Handle common result patterns
                if 'rows_returned' in result:
                    rows = result.get('rows_returned', 0)
                    total = result.get('total_matches', rows)
                    if total > rows:
                        return f"Found {total} rows (showing {rows})"
                    return f"Found {rows} row{'s' if rows != 1 else ''}"

                if 'sheets' in result:
                    count = len(result['sheets'])
                    return f"Found {count} sheet{'s' if count != 1 else ''}"

                if 'data' in result:
                    if isinstance(result['data'], list):
                        return f"Retrieved {len(result['data'])} record{'s' if len(result['data']) != 1 else ''}"

                # Generic dict result
                keys = len(result.keys())
                return f"Completed with {keys} field{'s' if keys != 1 else ''}"

            # Fallback for other types
            return "Completed successfully"

        except Exception:
            return "Completed"

    async def _execute_mcp_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> Any:
        """
        Execute MCP tool by name with analytics tracking

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            session_id: Optional session ID for analytics tracking

        Returns:
            Tool execution result
        """
        import time

        logger.info(f"Executing tool: {tool_name}")
        start_time = time.time()

        try:
            tools = mcp_server.list_tools()

            if tool_name not in tools:
                raise ValueError(f"Tool '{tool_name}' not found")

            tool_func = tools[tool_name]

            # Coerce string parameters to proper types (dict/list) using shared utility
            coerced_args = {key: coerce_string_to_type(value) for key, value in arguments.items()}

            # Log successful coercions
            for key, original_value in arguments.items():
                coerced_value = coerced_args[key]
                if original_value != coerced_value:
                    logger.info(f"Coerced parameter '{key}' from string to {type(coerced_value).__name__}")

            # Execute tool with coerced arguments
            result = tool_func(**coerced_args)

            duration_ms = int((time.time() - start_time) * 1000)

            # Track successful tool execution
            if session_id:
                await self._track_tool_call(
                    session_id=session_id,
                    tool_name=tool_name,
                    parameters=arguments,
                    duration_ms=duration_ms,
                    success=True
                )

            logger.info(f"Tool '{tool_name}' executed successfully in {duration_ms}ms")
            return result

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)

            # Track failed tool execution
            if session_id:
                await self._track_tool_call(
                    session_id=session_id,
                    tool_name=tool_name,
                    parameters=arguments,
                    duration_ms=duration_ms,
                    success=False,
                    error=str(e)
                )

            logger.error(f"Tool '{tool_name}' failed after {duration_ms}ms: {e}")
            raise

    async def _track_tool_call(
        self,
        session_id: str,
        tool_name: str,
        parameters: Dict[str, Any],
        duration_ms: int,
        success: bool,
        error: Optional[str] = None
    ):
        """
        Track MCP tool execution to analytics database.

        This runs asynchronously and won't affect tool execution performance.
        If tracking fails, it logs the error but doesn't raise exceptions.

        Args:
            session_id: Analytics session ID
            tool_name: Name of the executed tool
            parameters: Input parameters passed to the tool
            duration_ms: Execution duration in milliseconds
            success: Whether execution succeeded
            error: Error message if failed
        """
        try:
            from .database import AsyncSessionLocal
            from .services.analytics_service import AnalyticsService

            async with AsyncSessionLocal() as db:
                analytics = AnalyticsService(db)
                await analytics.track_tool_call(
                    session_id=session_id,
                    tool_name=tool_name,
                    parameters=parameters,
                    duration_ms=duration_ms,
                    success=success,
                    error=error
                )
                await db.commit()

            logger.debug(f"Tool call tracked: {tool_name} ({duration_ms}ms, success={success})")

        except Exception as e:
            # Don't let analytics failures affect tool execution
            logger.error(f"Failed to track tool call '{tool_name}': {e}")


# Singleton instance
claude_service = ClaudeLLMService()
