"""Service for loading and managing test configurations."""

import logging
from pathlib import Path
from typing import List, Optional, NamedTuple, Dict, Any

from ..models import TestCase, AgentTestSuite, ToolStubRequest


logger = logging.getLogger(__name__)


class TestLoadResult(NamedTuple):
    """Result of loading a test case from a YAML file."""
    test_name: str
    test_case: Optional[TestCase]
    error_message: Optional[str]
    file_path: Path
    
    @property
    def is_success(self) -> bool:
        """True if the test case was loaded successfully."""
        return self.test_case is not None and self.error_message is None


class TestConfigService:
    """Service for discovering and loading test configurations for AI agents."""
    
    def __init__(self, tests_root_dir: str = "tests"):
        """Initialize the test config service.
        
        Args:
            tests_root_dir: Root directory containing agent test directories
        """
        self.tests_root_dir = Path(tests_root_dir)
        
    def discover_agents(self) -> List[str]:
        """Discover all available agent test directories.
        
        Returns:
            List of agent names that have test directories
        """
        if not self.tests_root_dir.exists():
            logger.warning(f"Tests directory not found: {self.tests_root_dir}")
            return []
            
        agent_dirs = []
        for item in self.tests_root_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                # Check if directory contains YAML test files
                yaml_files = list(item.glob('*.yaml')) + list(item.glob('*.yml'))
                if yaml_files:
                    agent_dirs.append(item.name)
                    
        logger.info(f"Discovered {len(agent_dirs)} agent test directories: {agent_dirs}")
        return sorted(agent_dirs)
    
    def discover_test_files(self, agent_name: str) -> List[Path]:
        """Discover all test files for a specific agent.
        
        Args:
            agent_name: Name of the agent to find tests for
            
        Returns:
            List of paths to YAML test files
        """
        agent_dir = self.tests_root_dir / agent_name
        
        if not agent_dir.exists():
            raise FileNotFoundError(f"Agent test directory not found: {agent_dir}")
            
        # Find all YAML files in the agent directory
        yaml_files = []
        yaml_files.extend(agent_dir.glob('*.yaml'))
        yaml_files.extend(agent_dir.glob('*.yml'))
        
        # Filter out any hidden or backup files
        yaml_files = [f for f in yaml_files if not f.name.startswith('.')]
        
        logger.info(f"Found {len(yaml_files)} test files for agent '{agent_name}': {[f.name for f in yaml_files]}")
        return sorted(yaml_files)
    
    def load_test_case(self, test_file_path: Path) -> TestLoadResult:
        """Load a single test case from a YAML file.
        
        Args:
            test_file_path: Path to the YAML test file
            
        Returns:
            TestLoadResult with success/failure information
        """
        test_name = test_file_path.stem  # Get filename without extension
        
        try:
            test_case = TestCase.from_yaml_file(test_file_path)
            logger.debug(f"Successfully loaded test case: {test_case.test_name}")
            return TestLoadResult(
                test_name=test_case.test_name,
                test_case=test_case,
                error_message=None,
                file_path=test_file_path
            )
        except Exception as e:
            error_msg = f"YAML parsing error: {str(e)}"
            logger.error(f"Failed to load test case from {test_file_path}: {error_msg}")
            return TestLoadResult(
                test_name=test_name,
                test_case=None,
                error_message=error_msg,
                file_path=test_file_path
            )
    
    def load_agent_test_suite(self, agent_name: str) -> AgentTestSuite:
        """Load all test cases for an agent into a test suite.
        
        Args:
            agent_name: Name of the agent to load tests for
            
        Returns:
            AgentTestSuite containing all valid test cases for the agent
            
        Raises:
            FileNotFoundError: If agent test directory doesn't exist
            ValueError: If no valid test cases are found
        """
        logger.info(f"Loading test suite for agent: {agent_name}")
        
        # Discover test files
        test_files = self.discover_test_files(agent_name)
        
        if not test_files:
            raise ValueError(f"No test files found for agent: {agent_name}")
        
        # Load all test cases and track failures
        test_cases = []
        failed_loads = []
        
        for test_file in test_files:
            load_result = self.load_test_case(test_file)
            if load_result.is_success:
                test_cases.append(load_result.test_case)
            else:
                failed_loads.append({
                    "test_name": load_result.test_name,
                    "error": load_result.error_message,
                    "file_path": str(load_result.file_path)
                })
        
        # Log warnings for failed files
        if failed_loads:
            failed_names = [f["test_name"] for f in failed_loads]
            logger.warning(f"Failed to load {len(failed_loads)} test files: {failed_names}")
        
        # Create test suite (allows empty test_cases if there are failed_loads)
        if not test_cases and not failed_loads:
            raise ValueError(f"No test files found for agent: {agent_name}")
        
        test_suite = AgentTestSuite(
            agent_name=agent_name,
            test_cases=test_cases,
            failed_loads=failed_loads
        )
        
        # Load agent-level stubs if available
        agent_stubs = self._load_agent_stubs(agent_name)
        test_suite.agent_stubs = agent_stubs
        
        logger.info(f"Loaded test suite for '{agent_name}': {test_suite.total_tests} test cases")
        return test_suite
    
    def load_single_test(self, agent_name: str, test_name: str) -> AgentTestSuite:
        """Load a single test case for an agent.
        
        Args:
            agent_name: Name of the agent
            test_name: Name of the test file (without .yaml extension)
            
        Returns:
            AgentTestSuite containing only the specified test case
            
        Raises:
            FileNotFoundError: If agent test directory or test file doesn't exist
            ValueError: If the test case could not be loaded
        """
        logger.info(f"Loading single test '{test_name}' for agent: {agent_name}")
        
        # Construct test file path
        agent_dir = self.tests_root_dir / agent_name
        if not agent_dir.exists():
            raise FileNotFoundError(f"Agent test directory not found: {agent_dir}")
        
        # Try both .yaml and .yml extensions
        test_file = None
        for ext in ['.yaml', '.yml']:
            potential_file = agent_dir / f"{test_name}{ext}"
            if potential_file.exists():
                test_file = potential_file
                break
        
        if not test_file:
            raise FileNotFoundError(f"Test file not found: {test_name}.yaml (or .yml) in {agent_dir}")
        
        # Load the single test case
        load_result = self.load_test_case(test_file)
        
        if load_result.is_success:
            # Create test suite with single successful test
            test_suite = AgentTestSuite(
                agent_name=agent_name,
                test_cases=[load_result.test_case],
                failed_loads=[]
            )
        else:
            # Create test suite with single failed test
            test_suite = AgentTestSuite(
                agent_name=agent_name,
                test_cases=[],
                failed_loads=[{
                    "test_name": load_result.test_name,
                    "error": load_result.error_message,
                    "file_path": str(load_result.file_path)
                }]
            )
        
        # Load agent-level stubs if available
        agent_stubs = self._load_agent_stubs(agent_name)
        test_suite.agent_stubs = agent_stubs
        
        logger.info(f"Loaded single test '{test_name}' for '{agent_name}'")
        return test_suite
    
    def validate_agent_tests(self, agent_name: str) -> bool:
        """Validate all test configurations for an agent.
        
        Args:
            agent_name: Name of the agent to validate
            
        Returns:
            True if all tests are valid, False otherwise
        """
        try:
            test_suite = self.load_agent_test_suite(agent_name)
            logger.info(f"Validation successful for agent '{agent_name}': {test_suite.total_tests} valid tests")
            return True
        except Exception as e:
            logger.error(f"Validation failed for agent '{agent_name}': {e}")
            return False
    
    def get_agent_test_directory(self, agent_name: str) -> Path:
        """Get the test directory path for an agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Path to the agent's test directory
        """
        return self.tests_root_dir / agent_name
    
    def get_agent_stubs_directory(self, agent_name: str) -> Path:
        """Get the stubs directory path for an agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Path to the agent's stubs directory
        """
        return self.get_agent_test_directory(agent_name) / "stubs"
    
    def _load_agent_stubs(self, agent_name: str) -> Optional[Dict[str, List[ToolStubRequest]]]:
        """Load agent-level stubs from agent-services.yaml file.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Dictionary of agent-level stubs if file exists, None otherwise
        """
        agent_dir = self.tests_root_dir / agent_name
        agent_services_file = agent_dir / "agent-services.yaml"
        
        if not agent_services_file.exists():
            # Try alternative name
            agent_services_file = agent_dir / "agent-services.yml"
            
        if not agent_services_file.exists():
            logger.debug(f"No agent-services.yaml found for agent '{agent_name}'")
            return None
            
        try:
            import yaml
            with open(agent_services_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                
            if not data or 'agent_stubs' not in data:
                logger.warning(f"No 'agent_stubs' section found in {agent_services_file}")
                return None
                
            # Convert to ToolStubRequest objects
            agent_stubs = {}
            for tool_name, stub_configs in data['agent_stubs'].items():
                tool_stubs = []
                for stub_config in stub_configs:
                    tool_stub = ToolStubRequest(
                        request=stub_config.get('request', {}),
                        response_file=stub_config['response_file']
                    )
                    tool_stubs.append(tool_stub)
                agent_stubs[tool_name] = tool_stubs
                
            logger.info(f"Loaded agent-level stubs for '{agent_name}': {list(agent_stubs.keys())}")
            return agent_stubs
            
        except Exception as e:
            logger.error(f"Failed to load agent-services.yaml for '{agent_name}': {e}")
            return None