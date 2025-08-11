"""Service for building AI agent requests from test case data."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from uuid import uuid4

from ..models import TestCase, AgentRequest, AgentConfig, HttpRequest, HttpMethod, ToolStubRequest, LLMConfig


logger = logging.getLogger(__name__)


class RequestBuilderService:
    """Service for converting test case data into AI agent requests."""
    
    def __init__(self, agent_config: AgentConfig, tests_base_dir: str = "tests"):
        """Initialize the request builder service.
        
        Args:
            agent_config: Configuration for the AI agent
            tests_base_dir: Base directory containing test files and stubs
        """
        self.agent_config = agent_config
        self.tests_base_dir = Path(tests_base_dir)
        
    def build_agent_request(self, test_case: TestCase, session_id: Optional[str] = None) -> AgentRequest:
        """Build an AgentRequest from a test case.
        
        Args:
            test_case: Test case data from YAML
            session_id: Optional session ID for request tracking
            
        Returns:
            AgentRequest ready to be sent to the AI agent
        """
        logger.debug(f"Building agent request for test: {test_case.test_name}")
        
        # Generate session ID if not provided
        if not session_id:
            session_id = f"test-{test_case.test_name}-{uuid4().hex[:8]}"
        
        # Process tool stubs if present
        processed_tool_stubs = None
        if test_case.tool_stubs:
            processed_tool_stubs = self._process_tool_stubs(test_case)
        
        # Set up default LLM configuration
        llm_config = LLMConfig()
        
        # Create agent request
        agent_request = AgentRequest(
            user_input=test_case.user_input,
            variables=test_case.variables,
            session_id=session_id,
            tool_stubs=processed_tool_stubs,
            llm_config=llm_config
        )
        
        logger.info(f"Built agent request for '{test_case.test_name}' with session {session_id}")
        return agent_request
    
    def build_http_request(self, test_case: TestCase, endpoint_path: str = None,
                          session_id: Optional[str] = None) -> HttpRequest:
        """Build an HTTP request from a test case.
        
        Args:
            test_case: Test case data from YAML
            endpoint_path: API endpoint path (default: "/query")
            session_id: Optional session ID for request tracking
            
        Returns:
            HttpRequest ready to be sent via HttpClientService
        """
        # Check if this is a healthcheck test
        if test_case.test_name.lower() == "healthcheck":
            return self._build_healthcheck_request(test_case)
        
        # Build normal agent request
        agent_request = self.build_agent_request(test_case, session_id)
        
        # Use endpoint path from config if not provided
        if endpoint_path is None:
            endpoint_path = self.agent_config.endpoint_path
        
        # Construct full URL
        base_url = str(self.agent_config.base_url).rstrip('/')
        full_url = f"{base_url}{endpoint_path}"
        
        # Create HTTP request
        http_request = HttpRequest(
            method=HttpMethod.POST,
            url=full_url,
            json_data=agent_request.to_json_payload(),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-Test-Case": test_case.test_name
            }
        )
        
        logger.debug(f"Built HTTP request for '{test_case.test_name}': {http_request.method} {http_request.url}")
        return http_request
    
    def _build_healthcheck_request(self, test_case: TestCase) -> HttpRequest:
        """Build a healthcheck HTTP request.
        
        Args:
            test_case: Test case (should be named 'healthcheck')
            
        Returns:
            HttpRequest for healthcheck endpoint
        """
        # Construct healthcheck URL
        base_url = str(self.agent_config.base_url).rstrip('/')
        healthcheck_url = f"{base_url}/healthcheck"
        
        # Create simple GET request for healthcheck
        http_request = HttpRequest(
            method=HttpMethod.GET,
            url=healthcheck_url,
            headers={
                "Accept": "application/json",
                "X-Test-Case": test_case.test_name,
                "X-Test-Mode": "healthcheck"
            }
        )
        
        logger.info(f"Built healthcheck request for '{test_case.test_name}': GET {http_request.url}")
        return http_request
    
    def _process_tool_stubs(self, test_case: TestCase) -> Dict[str, List[ToolStubRequest]]:
        """Process tool stubs and load response data from files.
        
        Args:
            test_case: Test case containing tool stubs
            
        Returns:
            Processed tool stubs with loaded response data
        """
        if not test_case.tool_stubs:
            return {}
        
        processed_stubs = {}
        agent_stubs_dir = self.tests_base_dir / self.agent_config.agent_name / "stubs"
        
        for tool_name, stub_requests in test_case.tool_stubs.items():
            processed_requests = []
            
            for stub_request in stub_requests:
                # Load response data from file
                response_data = self._load_stub_response(agent_stubs_dir, stub_request.response_file)
                
                # Create processed stub request
                processed_request = ToolStubRequest(
                    request=stub_request.request,
                    response_file=stub_request.response_file
                )
                
                # Add the actual response data for the AI agent to use
                processed_request.response_data = response_data
                processed_requests.append(processed_request)
                
                logger.debug(f"Loaded stub for tool '{tool_name}': {stub_request.response_file}")
            
            processed_stubs[tool_name] = processed_requests
        
        logger.info(f"Processed {len(processed_stubs)} tool stubs for test '{test_case.test_name}'")
        return processed_stubs
    
    def _load_stub_response(self, stubs_dir: Path, response_file: str) -> Any:
        """Load response data from a stub file.
        
        Args:
            stubs_dir: Directory containing stub files
            response_file: Path to the response file (relative to stubs_dir)
            
        Returns:
            Loaded response data (parsed JSON or raw text)
        """
        # Handle different file path formats
        if response_file.endswith('.json'):
            file_path = stubs_dir / response_file
        else:
            # Assume JSON if no extension
            file_path = stubs_dir / f"{response_file}.json"
        
        if not file_path.exists():
            logger.warning(f"Stub response file not found: {file_path}")
            return {"error": f"Stub file not found: {response_file}"}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.suffix == '.json':
                    return json.load(f)
                else:
                    return f.read()
        except Exception as e:
            logger.error(f"Failed to load stub response from {file_path}: {e}")
            return {"error": f"Failed to load stub: {str(e)}"}
    
    def validate_test_case(self, test_case: TestCase) -> List[str]:
        """Validate a test case and return any validation errors.
        
        Args:
            test_case: Test case to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Check required fields
        if not test_case.user_input.strip():
            errors.append("user_input cannot be empty")
        
        if not test_case.expected_answer.strip():
            errors.append("expected_answer cannot be empty")
        
        if test_case.semantic_threshold < 0.0 or test_case.semantic_threshold > 1.0:
            errors.append("semantic_threshold must be between 0.0 and 1.0")
        
        # Validate tool stubs if present
        if test_case.tool_stubs:
            for tool_name, stub_requests in test_case.tool_stubs.items():
                for i, stub_request in enumerate(stub_requests):
                    if not isinstance(stub_request.request, dict):
                        errors.append(f"tool_stubs.{tool_name}[{i}].request must be a dictionary")
                    
                    if not stub_request.response_file:
                        errors.append(f"tool_stubs.{tool_name}[{i}].response_file cannot be empty")
                    
                    # Check if response file exists
                    agent_stubs_dir = self.tests_base_dir / self.agent_config.agent_name / "stubs"
                    response_file_path = agent_stubs_dir / stub_request.response_file
                    if not response_file_path.exists() and not (agent_stubs_dir / f"{stub_request.response_file}.json").exists():
                        errors.append(f"Stub response file not found: {stub_request.response_file}")
        
        return errors
    
    def create_request_summary(self, test_case: TestCase, agent_request: AgentRequest) -> Dict[str, Any]:
        """Create a summary of the request for logging/debugging.
        
        Args:
            test_case: Original test case
            agent_request: Built agent request
            
        Returns:
            Summary dictionary with key request information
        """
        summary = {
            "test_name": test_case.test_name,
            "session_id": agent_request.session_id,
            "user_input_length": len(agent_request.user_input),
            "has_variables": bool(agent_request.variables),
            "variables_count": len(agent_request.variables) if agent_request.variables else 0,
            "has_tool_stubs": bool(agent_request.tool_stubs),
            "tool_stubs_count": len(agent_request.tool_stubs) if agent_request.tool_stubs else 0,
            "expected_answer_length": len(test_case.expected_answer),
            "semantic_threshold": test_case.semantic_threshold
        }
        
        if agent_request.tool_stubs:
            summary["tool_names"] = list(agent_request.tool_stubs.keys())
            summary["total_stub_requests"] = sum(
                len(requests) for requests in agent_request.tool_stubs.values()
            )
        
        return summary
    
