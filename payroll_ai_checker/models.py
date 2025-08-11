"""Pydantic models for YAML configuration and test scenarios."""

from typing import Any, Dict, List, Optional, Union
from pathlib import Path
from enum import Enum
from ruamel.yaml import YAML
from pydantic import BaseModel, Field, HttpUrl, ConfigDict


class ToolStubRequest(BaseModel):
    """Individual tool stub request/response configuration."""
    request: Dict[str, Any]
    response_file: str
    response_data: Optional[Any] = None  # Loaded response data (set by RequestBuilderService)
    # Optional HTTP method and path template for generic routing
    method: Optional[str] = None  # e.g., "GET" or "POST"
    path_template: Optional[str] = None  # e.g., "/employees/{employeeId}/summary" or "/{id}"


class TestCase(BaseModel):
    """Individual test case configuration matching YAML structure."""
    test_name: str = ""  # Will be set from filename during loading
    variables: Optional[Dict[str, Any]] = {}
    user_input: str
    expected_answer: str
    semantic_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    comparison_method: str = Field(default="semantic")  # "semantic", "exact", or "substring"
    required_words: Optional[List[str]] = None  # For substring comparison
    tool_stubs: Optional[Dict[str, List[ToolStubRequest]]] = None
    
    @classmethod
    def from_yaml_file(cls, file_path: Union[str, Path]) -> "TestCase":
        """Load a test case from a YAML file."""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Test file not found: {file_path}")
            
        yaml = YAML(typ='safe')
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.load(f)
            
        # Handle empty or None data
        if data is None:
            data = {}
            
        # Use filename (without extension) as test_name instead of reading from YAML
        test_name = file_path.stem  # Gets filename without extension
        data['test_name'] = test_name
            
        # Convert tool_stubs format if present
        if 'tool_stubs' in data and data['tool_stubs']:
            tool_stubs = {}
            for tool_name, requests in data['tool_stubs'].items():
                tool_stubs[tool_name] = [
                    ToolStubRequest(**req) for req in requests
                ]
            data['tool_stubs'] = tool_stubs
            
        return cls(**data)


class TestResult(BaseModel):
    """Result of a test case execution."""
    test_name: str
    status: str  # "pass", "fail", "error"
    actual_response: Optional[str] = None
    expected_response: Optional[str] = None
    semantic_score: Optional[float] = None
    comparison_method: Optional[str] = None  # "exact", "semantic", "substring"
    comparison_details: Optional[str] = None  # Human-readable details about comparison
    error_message: Optional[str] = None
    execution_time_ms: Optional[float] = None
    tool_calls_made: Optional[List[Dict[str, Any]]] = None


class AgentTestSuite(BaseModel):
    """Collection of test cases for a specific agent."""
    agent_name: str
    test_cases: List[TestCase]
    failed_loads: List[Dict[str, str]] = Field(default_factory=list)  # List of {"test_name": str, "error": str, "file_path": str}
    agent_stubs: Optional[Dict[str, List[ToolStubRequest]]] = None  # Agent-level stubs for all tests
    total_tests: int = 0
    
    def __init__(self, **data):
        super().__init__(**data)
        # Total tests includes both successful and failed loads
        self.total_tests = len(self.test_cases) + len(self.failed_loads)


class TestReport(BaseModel):
    """Complete test execution report for an agent."""
    agent_name: str
    total_tests: int
    passed: int
    failed: int
    errors: int
    results: List[TestResult]
    execution_time_total_ms: Optional[float] = None
    
    @property
    def pass_percentage(self) -> float:
        """Calculate percentage of tests that passed."""
        if self.total_tests == 0:
            return 0.0
        return (self.passed / self.total_tests) * 100.0
    
    @property
    def fail_percentage(self) -> float:
        """Calculate percentage of tests that failed."""
        if self.total_tests == 0:
            return 0.0
        return (self.failed / self.total_tests) * 100.0
    
    @property
    def error_percentage(self) -> float:
        """Calculate percentage of tests that had errors."""
        if self.total_tests == 0:
            return 0.0
        return (self.errors / self.total_tests) * 100.0
    
    @property
    def success_rate(self) -> str:
        """Get formatted success rate string."""
        return f"{self.pass_percentage:.1f}%"
    
    @property
    def overall_status(self) -> str:
        """Get overall test run status."""
        if self.errors > 0:
            return "ERROR"
        elif self.failed > 0:
            return "FAILED"
        elif self.passed == self.total_tests:
            return "PASSED"
        else:
            return "INCOMPLETE"


# HTTP-related models for agent communication

class HttpMethod(str, Enum):
    """Supported HTTP methods for agent requests."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class AgentConfig(BaseModel):
    """Configuration for an AI agent endpoint."""
    agent_name: str
    base_url: HttpUrl
    endpoint_path: str  # Required: e.g., "/agent/payroll-us-agent-v1" or "/query"
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_delay_seconds: float = Field(default=1.0, ge=0.1, le=10.0)
    headers: Optional[Dict[str, str]] = None
    auth_header: Optional[str] = None  # e.g., "Bearer token123"
    cookie_header: Optional[str] = None  # e.g., "session=abc123; auth=xyz789"
    verify_ssl: bool = True


class HttpRequest(BaseModel):
    """HTTP request configuration for AI agent calls."""
    method: HttpMethod = HttpMethod.POST
    url: str
    headers: Optional[Dict[str, str]] = None
    json_data: Optional[Dict[str, Any]] = None
    form_data: Optional[Dict[str, str]] = None
    query_params: Optional[Dict[str, str]] = None
    timeout_seconds: Optional[int] = None


class HttpResponse(BaseModel):
    """HTTP response from AI agent."""
    status_code: int
    headers: Dict[str, str]
    text: str
    json_data: Optional[Dict[str, Any]] = None
    response_time_ms: float
    url: str
    
    model_config = ConfigDict(arbitrary_types_allowed=True)


class LLMConfig(BaseModel):
    """LLM configuration for AI agent requests."""
    model: str = Field(default="gpt-4.1-mini-2025-04-14")
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)


class AgentRequest(BaseModel):
    """Complete request to an AI agent including user input and tool stubs."""
    user_input: str
    variables: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    tool_stubs: Optional[Dict[str, List[ToolStubRequest]]] = None
    llm_config: Optional[LLMConfig] = None
    
    def to_json_payload(self) -> Dict[str, Any]:
        """Convert to JSON payload for HTTP request to AI agent.
        
        Only sends userInput, variables, and llm config - tool_stubs are used for 
        setting up mock services that the AI agent calls separately.
        """
        payload = {
            "userInput": self.user_input  # camelCase as expected by AI agent
        }
        
        if self.variables:
            payload["variables"] = self.variables
        
        # Add LLM configuration if provided, otherwise use defaults
        llm_config = self.llm_config or LLMConfig()
        payload["llm"] = {
            "model": llm_config.model,
            "temperature": llm_config.temperature
        }
        
        # Note: session_id and tool_stubs are NOT sent to the AI agent
        # - session_id is for internal tracking
        # - tool_stubs are used to configure mock services
        
        return payload


class AgentResponse(BaseModel):
    """Response from AI agent."""
    answer: str
    session_id: Optional[str] = None
    tool_calls_made: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_http_response(cls, http_response: HttpResponse) -> "AgentResponse":
        """Create AgentResponse from HTTP response."""
        if http_response.json_data:
            # Extract standard fields from JSON response
            data = http_response.json_data
            return cls(
                answer=data.get("answer", ""),
                session_id=data.get("session_id"),
                tool_calls_made=data.get("tool_calls_made"),
                metadata=data.get("metadata")
            )
        else:
            # Check if response is Server-Sent Events (SSE) format
            response_text = http_response.text or ""
            if "event:" in response_text and "data:" in response_text:
                parsed_answer = cls._parse_sse_response(response_text)
                session_id = cls._extract_session_id_from_sse(response_text)
                return cls(
                    answer=parsed_answer,
                    session_id=session_id
                )
            else:
                # If response is plain text, treat as answer
                return cls(answer=response_text)
    
    @classmethod
    def _parse_sse_response(cls, sse_text: str) -> str:
        """Parse Server-Sent Events response to extract the text answer."""
        lines = sse_text.strip().split('\n')
        text_parts = []
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('event: text'):
                # Look for the next data line
                if i + 1 < len(lines) and lines[i + 1].strip().startswith('data: '):
                    data_line = lines[i + 1].strip()
                    # Extract text after "data: "
                    text_content = data_line[6:]  # Remove "data: " prefix
                    if text_content:  # Only add non-empty content
                        text_parts.append(text_content)
            i += 1
        
        # Join all text parts to form the complete answer
        complete_answer = ''.join(text_parts)
        return complete_answer.strip()
    
    @classmethod
    def _extract_session_id_from_sse(cls, sse_text: str) -> Optional[str]:
        """Extract session ID from SSE response if present."""
        import json
        lines = sse_text.strip().split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('event: session-started'):
                # Look for the next data line
                if i + 1 < len(lines) and lines[i + 1].strip().startswith('data: '):
                    data_line = lines[i + 1].strip()
                    try:
                        # Extract JSON after "data: "
                        json_content = data_line[6:]  # Remove "data: " prefix
                        session_data = json.loads(json_content)
                        return str(session_data.get("sessionId"))
                    except (json.JSONDecodeError, KeyError):
                        pass
            i += 1
        
        return None