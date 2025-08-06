"""HTTP stub service for mocking tool endpoints during testing."""

import json
import logging
import threading
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from flask import Flask, request, jsonify
from werkzeug.serving import make_server

from ..models import TestCase, ToolStubRequest


logger = logging.getLogger(__name__)


class StubService:
    """HTTP server that provides mock tool endpoints for AI agent testing."""
    
    def __init__(self, port: int = 9876, host: str = "0.0.0.0"):
        """Initialize the stub service.
        
        Args:
            port: Port to run the HTTP server on
            host: Host to bind the server to
        """
        self.port = port
        self.host = host
        self.app = Flask(__name__)
        self.app.logger.setLevel(logging.WARNING)  # Reduce Flask noise
        self.server = None
        self.server_thread = None
        self.is_running = False
        
        # Storage for loaded tool stubs
        self.tool_stubs: Dict[str, List[ToolStubRequest]] = {}
        self.stubs_base_dir: Optional[Path] = None
        
        # Setup Flask routes
        self._setup_routes()
    
    def load_test_stubs(self, test_case: TestCase, stubs_base_dir: Path):
        """Load tool stubs from a test case.
        
        Args:
            test_case: Test case containing tool stub definitions
            stubs_base_dir: Base directory containing stub response files
        """
        self.stubs_base_dir = stubs_base_dir
        
        if test_case.tool_stubs:
            self.tool_stubs.update(test_case.tool_stubs)
            logger.info(f"Loaded tool stubs for test '{test_case.test_name}': {list(test_case.tool_stubs.keys())}")
    
    def clear_stubs(self):
        """Clear all loaded tool stubs."""
        self.tool_stubs.clear()
        logger.debug("Cleared all tool stubs")
    
    def start(self) -> bool:
        """Start the HTTP stub server.
        
        Returns:
            True if server started successfully, False otherwise
        """
        if self.is_running:
            logger.warning("Stub service is already running")
            return True
        
        try:
            self.server = make_server(self.host, self.port, self.app, threaded=True)
            self.server_thread = threading.Thread(target=self.server.serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()
            
            # Wait a moment to ensure server starts
            time.sleep(0.1)
            self.is_running = True
            
            logger.info(f"Stub service started on {self.host}:{self.port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start stub service: {e}")
            return False
    
    def stop(self):
        """Stop the HTTP stub server."""
        if not self.is_running:
            return
        
        try:
            if self.server:
                self.server.shutdown()
                
            if self.server_thread:
                self.server_thread.join(timeout=5.0)
            
            self.is_running = False
            logger.info("Stub service stopped")
            
        except Exception as e:
            logger.error(f"Error stopping stub service: {e}")
    
    def _setup_routes(self):
        """Setup Flask routes for tool endpoints."""
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint."""
            return jsonify({"status": "healthy", "service": "ai-answer-checker-stubs"})
        
        @self.app.route('/api/mcp/service/<service_name>', methods=['GET'])
        def handle_mcp_service_definition(service_name: str):
            """Handle MCP service definition requests."""
            try:
                endpoint_path = f"api/mcp/service/{service_name}"
                logger.info(f"MCP service definition request: {endpoint_path}")
                
                # Find matching stub
                mock_response = self._find_matching_stub(endpoint_path, {})
                
                if mock_response is not None:
                    logger.debug(f"Returning MCP service definition for {service_name}")
                    return jsonify(mock_response)
                else:
                    logger.warning(f"No MCP service definition found for {service_name}")
                    return jsonify({"error": f"MCP service '{service_name}' not found"}), 404
                    
            except Exception as e:
                logger.error(f"Error handling MCP service definition for {service_name}: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/<tool_name>', methods=['GET', 'POST'])
        def handle_tool_request(tool_name: str):
            """Handle tool requests from the AI agent.
            
            Args:
                tool_name: Name of the tool being called
            """
            try:
                # Get request parameters
                if request.method == 'GET':
                    request_params = dict(request.args)
                else:  # POST
                    request_params = request.get_json() or {}
                
                logger.info(f"Tool request: {tool_name} with params: {request_params}")
                
                # Find matching stub
                mock_response = self._find_matching_stub(tool_name, request_params)
                
                if mock_response is not None:
                    logger.debug(f"Returning mock response for {tool_name}")
                    return jsonify(mock_response)
                else:
                    logger.warning(f"No matching stub found for {tool_name} with params: {request_params}")
                    return jsonify({"error": f"No mock data found for tool '{tool_name}'"}), 404
                    
            except Exception as e:
                logger.error(f"Error handling tool request for {tool_name}: {e}")
                return jsonify({"error": str(e)}), 500
    
    def _find_matching_stub(self, tool_name: str, request_params: Dict[str, Any]) -> Optional[Any]:
        """Find a matching stub response for the given tool and parameters.
        
        Args:
            tool_name: Name of the tool
            request_params: Parameters from the request
            
        Returns:
            Mock response data if found, None otherwise
        """
        if tool_name not in self.tool_stubs:
            return None
        
        # Try to find a matching stub request
        for stub_request in self.tool_stubs[tool_name]:
            if self._params_match(stub_request.request, request_params):
                # Load and return the response data
                return self._load_response_data(stub_request.response_file)
        
        # If no exact match, return the first available stub (for flexibility)
        if self.tool_stubs[tool_name]:
            first_stub = self.tool_stubs[tool_name][0]
            logger.info(f"No exact parameter match for {tool_name}, using first available stub")
            return self._load_response_data(first_stub.response_file)
        
        return None
    
    def _params_match(self, stub_params: Dict[str, Any], request_params: Dict[str, Any]) -> bool:
        """Check if request parameters match stub parameters.
        
        Args:
            stub_params: Parameters defined in the stub
            request_params: Parameters from the actual request
            
        Returns:
            True if parameters match, False otherwise
        """
        # Convert request params to match stub format
        normalized_request = {}
        for key, value in request_params.items():
            if isinstance(value, str) and value.isdigit():
                # Convert string numbers to integers
                normalized_request[key] = int(value)
            elif isinstance(value, str) and ',' in value:
                # Handle comma-separated values like "999999,999998" -> [999999, 999998]
                try:
                    normalized_request[key] = [int(x.strip()) for x in value.split(',')]
                except ValueError:
                    normalized_request[key] = [x.strip() for x in value.split(',')]
            else:
                normalized_request[key] = value
        
        # Check if all stub parameters are present in the request
        for key, expected_value in stub_params.items():
            if key not in normalized_request:
                return False
            
            actual_value = normalized_request[key]
            
            # Handle list comparisons with flexibility
            if isinstance(expected_value, list) and isinstance(actual_value, list):
                # Both are lists - compare as sets
                if set(expected_value) != set(actual_value):
                    return False
            elif isinstance(expected_value, list) and not isinstance(actual_value, list):
                # Stub expects list, request has single value - check if single value is in list
                if actual_value not in expected_value:
                    return False
            elif not isinstance(expected_value, list) and isinstance(actual_value, list):
                # Stub expects single value, request has list - check if expected value is in list
                if expected_value not in actual_value:
                    return False
            elif expected_value != actual_value:
                # Both are single values - direct comparison
                return False
        
        return True
    
    def _load_response_data(self, response_file: str) -> Any:
        """Load response data from a stub file.
        
        Args:
            response_file: Path to the response file (relative to stubs_base_dir)
            
        Returns:
            Loaded response data
        """
        if not self.stubs_base_dir:
            logger.error("Stubs base directory not set")
            return {"error": "Stubs not configured"}
        
        # Handle different file path formats
        if response_file.endswith('.json'):
            file_path = self.stubs_base_dir / response_file
        else:
            file_path = self.stubs_base_dir / f"{response_file}.json"
        
        if not file_path.exists():
            logger.error(f"Stub response file not found: {file_path}")
            return {"error": f"Stub file not found: {response_file}"}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load stub response from {file_path}: {e}")
            return {"error": f"Failed to load stub: {str(e)}"}
    
    def get_stub_info(self) -> Dict[str, Any]:
        """Get information about currently loaded stubs.
        
        Returns:
            Dictionary with stub information
        """
        return {
            "is_running": self.is_running,
            "host": self.host,
            "port": self.port,
            "loaded_tools": list(self.tool_stubs.keys()),
            "total_stubs": sum(len(stubs) for stubs in self.tool_stubs.values())
        }
    
    def load_agent_stubs(self, tool_name: str, tool_stubs: List[ToolStubRequest], stubs_base_dir: Path):
        """Load agent-level stubs for a specific tool.
        
        Args:
            tool_name: Name of the tool (e.g., 'api/mcp/service/payDetailsMCP')
            tool_stubs: List of ToolStubRequest objects for this tool
            stubs_base_dir: Base directory containing stub response files
        """
        if not self.stubs_base_dir:
            self.stubs_base_dir = stubs_base_dir
        
        # Initialize tool stubs if not already present
        if tool_name not in self.tool_stubs:
            self.tool_stubs[tool_name] = []
        
        # Add agent-level stubs (they get priority since they're loaded first)
        for stub_request in tool_stubs:
            # Load response data immediately
            response_data = self._load_response_data(stub_request.response_file)
            stub_request.response_data = response_data
            
            # Add to the beginning of the list (higher priority than test-specific stubs)
            self.tool_stubs[tool_name].insert(0, stub_request)
        
        logger.debug(f"Loaded {len(tool_stubs)} agent-level stubs for tool '{tool_name}'")