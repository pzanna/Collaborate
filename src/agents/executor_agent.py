"""
Executor Agent for task execution and automation.

This module provides the ExecutorAgent that handles code execution,
API calls, data processing, and file operations for the research system.
"""

import asyncio
import logging
import subprocess
import tempfile
import os
import json
import requests
from typing import Dict, List, Any, Optional
from pathlib import Path
import aiohttp
import aiofiles

from .base_agent import BaseAgent, AgentStatus
from ..mcp.protocols import ResearchAction
from ..config.config_manager import ConfigManager


class ExecutorAgent(BaseAgent):
    """
    Executor Agent for task execution and automation.
    
    This agent handles:
    - Code execution (sandboxed)
    - API calls and HTTP requests
    - Data processing and transformation
    - File operations and I/O
    - System command execution
    - Database operations
    """
    
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the Executor Agent.
        
        Args:
            config_manager: Configuration manager instance
        """
        super().__init__("executor", config_manager)
        
        # Execution configuration
        self.sandbox_enabled = True
        self.max_execution_time = 30  # seconds
        self.allowed_imports = {
            'pandas', 'numpy', 'json', 'csv', 'datetime', 'math', 'statistics',
            'requests', 'urllib', 'pathlib', 'os', 'sys', 'io', 'collections'
        }
        
        # Working directory for temporary files
        self.work_dir = Path(tempfile.mkdtemp(prefix="executor_"))
        
        # HTTP session for API calls
        self.http_session: Optional[aiohttp.ClientSession] = None
        
        self.logger.info("ExecutorAgent initialized")
    
    def _get_capabilities(self) -> List[str]:
        """Get executor agent capabilities."""
        return [
            'execute_code',
            'make_api_call',
            'process_data',
            'read_file',
            'write_file',
            'run_command',
            'transform_data',
            'validate_data',
            'execute_research'
        ]
    
    async def _initialize_agent(self) -> None:
        """Initialize executor-specific resources."""
        # Create HTTP session
        self.http_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        
        # Ensure work directory exists
        self.work_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up security restrictions
        self._setup_security_restrictions()
        
        self.logger.info(f"ExecutorAgent initialized with work directory: {self.work_dir}")
    
    async def _cleanup_agent(self) -> None:
        """Clean up executor-specific resources."""
        # Close HTTP session
        if self.http_session:
            await self.http_session.close()
        
        # Clean up temporary files
        try:
            import shutil
            shutil.rmtree(self.work_dir, ignore_errors=True)
        except Exception as e:
            self.logger.warning(f"Failed to clean up work directory: {e}")
        
        self.logger.info("ExecutorAgent cleanup completed")
    
    async def _process_task_impl(self, task: ResearchAction) -> Dict[str, Any]:
        """
        Process an execution task.
        
        Args:
            task: Research task to process
            
        Returns:
            Dict[str, Any]: Execution results
        """
        action = task.action
        payload = task.payload
        
        if action == 'execute_code':
            return await self._execute_code(payload)
        elif action == 'make_api_call':
            return await self._make_api_call(payload)
        elif action == 'process_data':
            return await self._process_data(payload)
        elif action == 'read_file':
            return await self._read_file(payload)
        elif action == 'write_file':
            return await self._write_file(payload)
        elif action == 'run_command':
            return await self._run_command(payload)
        elif action == 'transform_data':
            return await self._transform_data(payload)
        elif action == 'validate_data':
            return await self._validate_data(payload)
        elif action == 'execute_research':
            return await self._execute_research(payload)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def _execute_code(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Python code in a sandboxed environment.
        
        Args:
            payload: Code execution parameters
            
        Returns:
            Dict[str, Any]: Execution results
        """
        code = payload.get('code', '')
        language = payload.get('language', 'python')
        timeout = payload.get('timeout', self.max_execution_time)
        
        if not code:
            raise ValueError("Code is required for execution")
        
        if language != 'python':
            raise ValueError(f"Unsupported language: {language}")
        
        # Create temporary file for code
        code_file = self.work_dir / f"exec_{asyncio.get_event_loop().time()}.py"
        
        try:
            # Write code to temporary file
            async with aiofiles.open(code_file, 'w') as f:
                await f.write(code)
            
            # Execute code with timeout
            result = await self._run_python_code(code_file, timeout)
            
            return {
                'success': True,
                'output': result['stdout'],
                'error': result['stderr'],
                'return_code': result['return_code'],
                'execution_time': result['execution_time']
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'output': '',
                'return_code': -1,
                'execution_time': 0
            }
        finally:
            # Clean up temporary file
            try:
                code_file.unlink(missing_ok=True)
            except Exception:
                pass
    
    async def _make_api_call(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make HTTP API call.
        
        Args:
            payload: API call parameters
            
        Returns:
            Dict[str, Any]: API response
        """
        url = payload.get('url', '')
        method = payload.get('method', 'GET').upper()
        headers = payload.get('headers', {})
        params = payload.get('params', {})
        data = payload.get('data', None)
        json_data = payload.get('json', None)
        
        if not url:
            raise ValueError("URL is required for API call")
        
        if not self.http_session:
            raise RuntimeError("HTTP session not initialized")
        
        try:
            async with self.http_session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                data=data,
                json=json_data
            ) as response:
                
                # Get response content
                content_type = response.headers.get('Content-Type', '')
                
                if 'application/json' in content_type:
                    response_data = await response.json()
                else:
                    response_data = await response.text()
                
                return {
                    'success': True,
                    'status_code': response.status,
                    'headers': dict(response.headers),
                    'data': response_data,
                    'url': str(response.url)
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'status_code': 0,
                'headers': {},
                'data': None,
                'url': url
            }
    
    async def _process_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and analyze data.
        
        Args:
            payload: Data processing parameters
            
        Returns:
            Dict[str, Any]: Processing results
        """
        data = payload.get('data', [])
        operation = payload.get('operation', 'analyze')
        
        if not data:
            raise ValueError("Data is required for processing")
        
        try:
            if operation == 'analyze':
                result = self._analyze_data(data)
            elif operation == 'summarize':
                result = self._summarize_data(data)
            elif operation == 'aggregate':
                result = self._aggregate_data(data)
            elif operation == 'filter':
                filters = payload.get('filters', {})
                result = self._filter_data(data, filters)
            elif operation == 'sort':
                sort_key = payload.get('sort_key', '')
                result = self._sort_data(data, sort_key)
            else:
                raise ValueError(f"Unknown operation: {operation}")
            
            return {
                'success': True,
                'result': result,
                'operation': operation,
                'input_size': len(data)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'operation': operation,
                'input_size': len(data) if data else 0
            }
    
    async def _read_file(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Read file contents.
        
        Args:
            payload: File reading parameters
            
        Returns:
            Dict[str, Any]: File contents
        """
        file_path = payload.get('file_path', '')
        encoding = payload.get('encoding', 'utf-8')
        max_size = payload.get('max_size', 1024 * 1024)  # 1MB limit
        
        if not file_path:
            raise ValueError("File path is required")
        
        # Security check: only allow reading from work directory
        full_path = Path(file_path)
        if not self._is_safe_path(full_path):
            raise ValueError("File path not allowed")
        
        try:
            # Check file size
            if full_path.stat().st_size > max_size:
                raise ValueError(f"File too large (max {max_size} bytes)")
            
            # Read file content
            async with aiofiles.open(full_path, 'r', encoding=encoding) as f:
                content = await f.read()
            
            return {
                'success': True,
                'content': content,
                'file_path': str(full_path),
                'size': len(content),
                'encoding': encoding
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'file_path': file_path,
                'size': 0,
                'encoding': encoding
            }
    
    async def _write_file(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Write content to file.
        
        Args:
            payload: File writing parameters
            
        Returns:
            Dict[str, Any]: Write results
        """
        file_path = payload.get('file_path', '')
        content = payload.get('content', '')
        encoding = payload.get('encoding', 'utf-8')
        append = payload.get('append', False)
        
        if not file_path:
            raise ValueError("File path is required")
        
        # Security check: only allow writing to work directory
        full_path = Path(file_path)
        if not self._is_safe_path(full_path):
            raise ValueError("File path not allowed")
        
        try:
            # Ensure directory exists
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file content
            mode = 'a' if append else 'w'
            async with aiofiles.open(full_path, mode, encoding=encoding) as f:
                await f.write(content)
            
            return {
                'success': True,
                'file_path': str(full_path),
                'size': len(content),
                'encoding': encoding,
                'append': append
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'file_path': file_path,
                'size': 0,
                'encoding': encoding,
                'append': append
            }
    
    async def _run_command(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run system command.
        
        Args:
            payload: Command execution parameters
            
        Returns:
            Dict[str, Any]: Command results
        """
        command = payload.get('command', '')
        timeout = payload.get('timeout', 30)
        working_dir = payload.get('working_dir', str(self.work_dir))
        
        if not command:
            raise ValueError("Command is required")
        
        # Security check: only allow safe commands
        if not self._is_safe_command(command):
            raise ValueError("Command not allowed")
        
        try:
            # Run command with timeout
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=timeout
            )
            
            return {
                'success': True,
                'stdout': stdout.decode('utf-8'),
                'stderr': stderr.decode('utf-8'),
                'return_code': process.returncode,
                'command': command
            }
            
        except asyncio.TimeoutError:
            return {
                'success': False,
                'error': 'Command timeout',
                'stdout': '',
                'stderr': '',
                'return_code': -1,
                'command': command
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'stdout': '',
                'stderr': '',
                'return_code': -1,
                'command': command
            }
    
    async def _transform_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Transform data between formats."""
        data = payload.get('data', [])
        from_format = payload.get('from_format', 'json')
        to_format = payload.get('to_format', 'csv')
        
        try:
            if from_format == 'json' and to_format == 'csv':
                result = self._json_to_csv(data)
            elif from_format == 'csv' and to_format == 'json':
                result = self._csv_to_json(data)
            else:
                raise ValueError(f"Unsupported transformation: {from_format} to {to_format}")
            
            return {
                'success': True,
                'result': result,
                'from_format': from_format,
                'to_format': to_format
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'from_format': from_format,
                'to_format': to_format
            }
    
    async def _validate_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data against schema."""
        data = payload.get('data', [])
        schema = payload.get('schema', {})
        
        try:
            validation_result = self._validate_against_schema(data, schema)
            
            return {
                'success': True,
                'valid': validation_result['valid'],
                'errors': validation_result['errors'],
                'data_size': len(data)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'valid': False,
                'errors': [],
                'data_size': len(data) if data else 0
            }
    
    async def _run_python_code(self, code_file: Path, timeout: int) -> Dict[str, Any]:
        """Run Python code file with timeout."""
        start_time = asyncio.get_event_loop().time()
        
        process = await asyncio.create_subprocess_exec(
            'python', str(code_file),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.work_dir)
        )
        
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), 
            timeout=timeout
        )
        
        execution_time = asyncio.get_event_loop().time() - start_time
        
        return {
            'stdout': stdout.decode('utf-8'),
            'stderr': stderr.decode('utf-8'),
            'return_code': process.returncode,
            'execution_time': execution_time
        }
    
    def _setup_security_restrictions(self) -> None:
        """Set up security restrictions for code execution."""
        # TODO: Implement comprehensive security restrictions
        self.logger.info("Security restrictions enabled for code execution")
    
    def _is_safe_path(self, path: Path) -> bool:
        """Check if file path is safe for operations."""
        try:
            # Resolve path and check if it's within work directory
            resolved = path.resolve()
            return str(resolved).startswith(str(self.work_dir.resolve()))
        except Exception:
            return False
    
    def _is_safe_command(self, command: str) -> bool:
        """Check if command is safe to execute."""
        # Only allow basic file operations and data processing commands
        safe_commands = {
            'ls', 'cat', 'head', 'tail', 'wc', 'grep', 'sort', 'uniq',
            'python', 'pip', 'node', 'npm'
        }
        
        command_parts = command.split()
        if not command_parts:
            return False
        
        base_command = command_parts[0]
        return base_command in safe_commands
    
    def _analyze_data(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze data and return statistics."""
        if not data:
            return {'count': 0, 'fields': []}
        
        # Basic analysis
        count = len(data)
        fields = list(data[0].keys()) if data else []
        
        # Field analysis
        field_stats = {}
        for field in fields:
            values = [item.get(field) for item in data if field in item]
            field_stats[field] = {
                'count': len(values),
                'non_null': len([v for v in values if v is not None]),
                'unique': len(set(str(v) for v in values if v is not None))
            }
        
        return {
            'count': count,
            'fields': fields,
            'field_stats': field_stats
        }
    
    def _summarize_data(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Summarize data."""
        analysis = self._analyze_data(data)
        
        return {
            'summary': f"Dataset with {analysis['count']} records and {len(analysis['fields'])} fields",
            'fields': analysis['fields'],
            'record_count': analysis['count']
        }
    
    def _aggregate_data(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate data by common fields."""
        # Simple aggregation - count by first field
        if not data:
            return {}
        
        fields = list(data[0].keys())
        if not fields:
            return {}
        
        # Group by first field
        groups = {}
        first_field = fields[0]
        
        for item in data:
            key = item.get(first_field, 'unknown')
            if key not in groups:
                groups[key] = []
            groups[key].append(item)
        
        # Return counts
        return {field: len(items) for field, items in groups.items()}
    
    def _filter_data(self, data: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Filter data based on criteria."""
        filtered = []
        
        for item in data:
            match = True
            for key, value in filters.items():
                if key not in item or item[key] != value:
                    match = False
                    break
            
            if match:
                filtered.append(item)
        
        return filtered
    
    def _sort_data(self, data: List[Dict[str, Any]], sort_key: str) -> List[Dict[str, Any]]:
        """Sort data by specified key."""
        if not sort_key:
            return data
        
        return sorted(data, key=lambda x: x.get(sort_key, ''))
    
    def _json_to_csv(self, data: List[Dict[str, Any]]) -> str:
        """Convert JSON data to CSV format."""
        if not data:
            return ''
        
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        
        return output.getvalue()
    
    def _csv_to_json(self, csv_data: str) -> List[Dict[str, Any]]:
        """Convert CSV data to JSON format."""
        import csv
        import io
        
        reader = csv.DictReader(io.StringIO(csv_data))
        return list(reader)
    
    def _validate_against_schema(self, data: List[Dict[str, Any]], schema: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data against a simple schema."""
        errors = []
        
        required_fields = schema.get('required', [])
        field_types = schema.get('types', {})
        
        for i, item in enumerate(data):
            # Check required fields
            for field in required_fields:
                if field not in item:
                    errors.append(f"Row {i}: Missing required field '{field}'")
            
            # Check field types
            for field, expected_type in field_types.items():
                if field in item:
                    value = item[field]
                    if expected_type == 'string' and not isinstance(value, str):
                        errors.append(f"Row {i}: Field '{field}' should be string, got {type(value).__name__}")
                    elif expected_type == 'number' and not isinstance(value, (int, float)):
                        errors.append(f"Row {i}: Field '{field}' should be number, got {type(value).__name__}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }

    async def _execute_research(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute research-related tasks.
        
        Args:
            payload: Research execution parameters
            
        Returns:
            Dict[str, Any]: Execution results
        """
        try:
            query = payload.get('query', '')
            context = payload.get('context', {})
            execution_type = payload.get('execution_type', 'basic')
            
            self.logger.info(f"Executing research task for query: {query}")
            
            # For now, this is a simple implementation that logs the research context
            # and returns a summary. In a full implementation, this could:
            # - Execute code to analyze data
            # - Make API calls to external services
            # - Process files and documents
            # - Run computational tasks
            
            results = []
            
            # Process search results if available
            search_results = context.get('search_results', [])
            if search_results:
                results.append({
                    'type': 'search_analysis',
                    'description': f"Analyzed {len(search_results)} search results",
                    'data': {
                        'result_count': len(search_results),
                        'sources': [result.get('url', 'Unknown') for result in search_results[:5]]
                    }
                })
            
            # Process reasoning output if available
            reasoning_output = context.get('reasoning_output', '')
            if reasoning_output:
                # Handle both string and dict formats for reasoning output
                if isinstance(reasoning_output, str):
                    analysis_text = reasoning_output
                    analysis_length = len(reasoning_output)
                elif isinstance(reasoning_output, dict):
                    analysis_text = str(reasoning_output.get('analysis', ''))
                    analysis_length = len(analysis_text)
                else:
                    analysis_text = str(reasoning_output)
                    analysis_length = len(analysis_text)
                
                results.append({
                    'type': 'reasoning_analysis',
                    'description': "Processed reasoning analysis",
                    'data': {
                        'analysis_length': analysis_length,
                        'has_insights': 'insight' in analysis_text.lower() or 'finding' in analysis_text.lower(),
                        'preview': analysis_text[:200] + '...' if len(analysis_text) > 200 else analysis_text
                    }
                })
            
            # Process any additional context data
            memory_data = context.get('memory_data', {})
            if memory_data:
                results.append({
                    'type': 'memory_integration',
                    'description': "Integrated memory data",
                    'data': {
                        'memory_entries': len(memory_data.get('entries', [])),
                        'has_historical_context': bool(memory_data.get('relevant_history', []))
                    }
                })
            
            # Process file data if available
            file_data = context.get('file_data', [])
            if file_data:
                results.append({
                    'type': 'file_processing',
                    'description': f"Processed {len(file_data)} files",
                    'data': {
                        'file_count': len(file_data),
                        'file_types': list(set(f.get('type', 'unknown') for f in file_data))
                    }
                })
            
            # Generate execution insights
            insights = []
            if search_results and reasoning_output:
                insights.append("Successfully combined search results with reasoning analysis")
            if len(results) > 1:
                insights.append(f"Integrated {len(results)} different data sources")
            
            if insights:
                results.append({
                    'type': 'execution_insights',
                    'description': "Generated execution insights",
                    'data': {
                        'insights': insights,
                        'integration_success': True
                    }
                })
            
            # Create execution summary
            execution_summary = {
                'query': query,
                'execution_type': execution_type,
                'total_results': len(results),
                'status': 'completed',
                'timestamp': asyncio.get_event_loop().time()
            }
            
            self.logger.info(f"Research execution completed with {len(results)} results")
            
            return {
                'results': results,
                'summary': execution_summary,
                'status': 'completed'
            }
            
        except Exception as e:
            self.logger.error(f"Research execution failed: {e}")
            return {
                'results': [],
                'summary': {
                    'query': payload.get('query', ''),
                    'status': 'failed',
                    'error': str(e)
                },
                'status': 'failed',
                'error': str(e)
            }
