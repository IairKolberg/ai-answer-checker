"""Main orchestration logic for AI answer checking regression tests."""

import logging
import sys
import time
from pathlib import Path
from typing import List, Optional

from click import clear

from .models import (
    AgentTestSuite, TestReport, TestResult, TestCase, 
    AgentResponse, HttpResponse
)
from .services import (
    TestConfigService, AgentConfigService, 
    HttpClientService, RequestBuilderService, ResponseComparisonService, ReportWriterService,
    StubService
)


logger = logging.getLogger(__name__)


class TestRunner:
    """Main test runner for AI answer regression tests."""
    
    def __init__(self, tests_dir: str = "agent_tests", configs_dir: str = "configs", reports_dir: str = "reports"):
        """Initialize the test runner.
        
        Args:
            tests_dir: Directory containing test configurations
            configs_dir: Directory containing agent configurations
            reports_dir: Directory to write report files to
        """
        self.test_service = TestConfigService(tests_dir)
        self.config_service = AgentConfigService(configs_dir)
        self.comparison_service = ResponseComparisonService()
        self.report_writer = ReportWriterService(reports_dir)
        self.stub_service = StubService()
        self.tests_dir = tests_dir
        
    def load_agent_tests(self, agent_name: str) -> AgentTestSuite:
        """Load test suite for a specific agent.
        
        Args:
            agent_name: Name of the agent to load tests for
            
        Returns:
            AgentTestSuite containing all test cases for the agent
        """
        logger.info(f"Loading test suite for agent: {agent_name}")
        return self.test_service.load_agent_test_suite(agent_name)
    
    def run_tests_from_suite(self, test_suite: AgentTestSuite, environment: str = "dev", 
                            dry_run: bool = False, write_reports: bool = True, keep_stubs: bool = False, no_stubs: bool = False) -> TestReport:
        """Run tests from a pre-loaded test suite.
        
        Args:
            test_suite: Pre-loaded test suite to execute
            environment: Environment to test against (dev, staging, prod)
            dry_run: If True, validate and build requests but don't send them
            write_reports: If True, write report files to disk
            keep_stubs: If True, keep stub service running after tests complete
            no_stubs: If True, skip stub service and test against real services
            
        Returns:
            TestReport with execution results
        """
        start_time = time.time()
        agent_name = test_suite.agent_name
        logger.info(f"Running tests for agent: {agent_name} (environment: {environment})")
        
        try:
            # Load agent configuration
            agent_config = self.config_service.get_agent_config(agent_name, environment)
            
            # Start stub service for tool mocking (unless disabled)
            stub_started = False
            if not dry_run and not no_stubs:
                # Load tool stubs from all test cases and agent-level stubs
                stubs_base_dir = Path(self.tests_dir) / agent_name / "stubs"
                
                # Load agent-level stubs first (if any)
                if test_suite.agent_stubs:
                    logger.info(f"Loading agent-level stubs: {list(test_suite.agent_stubs.keys())}")
                    for tool_name, tool_stubs in test_suite.agent_stubs.items():
                        self.stub_service.load_agent_stubs(tool_name, tool_stubs, stubs_base_dir)
                
                # Load test-specific stubs
                for test_case in test_suite.test_cases:
                    if test_case.tool_stubs:
                        self.stub_service.load_test_stubs(test_case, stubs_base_dir)
                
                # Start the stub HTTP server
                if self.stub_service.start():
                    stub_started = True
                    logger.info(f"Stub service started on port {self.stub_service.port} for {len(self.stub_service.tool_stubs)} tools")
                else:
                    logger.warning("Failed to start stub service - tool calls may fail")
            
            # Initialize services
            request_builder = RequestBuilderService(agent_config, self.tests_dir)
            
            # Initialize results tracking
            results = []
            passed = 0
            failed = 0
            errors = 0
            
            # Create HTTP client (only if not dry run)
            http_client = None
            if not dry_run:
                http_client = HttpClientService(agent_config)
            
            try:
                # Create error results for failed YAML loads
                for failed_load in test_suite.failed_loads:
                    error_result = TestResult(
                        test_name=failed_load["test_name"],
                        status="error",
                        error_message=failed_load["error"],
                        execution_time_ms=0.0
                    )
                    results.append(error_result)
                    errors += 1
                
                # Run each successfully loaded test case
                for test_case in test_suite.test_cases:
                    result = self._run_single_test(
                        test_case, request_builder, http_client, dry_run
                    )
                    results.append(result)
                    
                    # Update counters
                    if result.status == "pass":
                        passed += 1
                    elif result.status == "fail":
                        failed += 1
                    else:
                        errors += 1
            
            finally:
                # Clean up HTTP client
                if http_client:
                    http_client.close()
                
                # Stop stub service (unless keep_stubs is True)
                if stub_started:
                    if keep_stubs:
                        logger.info(f"🔧 Stub service kept running on port {self.stub_service.port} for manual testing")
                        logger.info(f"📋 Available stub endpoints:")
                        for tool_name in self.stub_service.tool_stubs.keys():
                            logger.info(f"   • GET/POST http://localhost:{self.stub_service.port}/{tool_name}")
                        logger.info(f"   • Health check: http://localhost:{self.stub_service.port}/health")
                        logger.info(f"🛑 To stop the stub service manually, press Ctrl+C or restart the application")
                    else:
                        self.stub_service.stop()
                        logger.info("Stub service stopped")
            
            # Calculate total execution time
            total_time_ms = (time.time() - start_time) * 1000
            
            # Create test report
            report = TestReport(
                agent_name=agent_name,
                total_tests=test_suite.total_tests,
                passed=passed,
                failed=failed,
                errors=errors,
                results=results,
                execution_time_total_ms=total_time_ms
            )
            
            # Add test cases mapping for CSV report generation
            report._test_cases_map = {test_case.test_name: test_case for test_case in test_suite.test_cases}
            
            # Write report files if requested
            if write_reports:
                try:
                    written_files = self.report_writer.write_report(report)
                    if 'csv' in written_files:
                        logger.info(f"CSV report written: {written_files['csv']}")
                except Exception as e:
                    logger.error(f"Failed to write report files: {e}")
            
            logger.info(f"Test run completed for '{agent_name}': {passed} passed, {failed} failed, {errors} errors")
            return report
            
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            raise
    
    def run_agent_tests(self, agent_name: str, environment: str = "dev", 
                       dry_run: bool = False, write_reports: bool = True) -> TestReport:
        """Run all tests for a specific agent.
        
        Args:
            agent_name: Name of the agent to test
            environment: Environment to test against (dev, staging, prod)
            dry_run: If True, validate and build requests but don't send them
            write_reports: If True, write report files to disk
            
        Returns:
            TestReport with execution results
        """
        # Load test suite and delegate to run_tests_from_suite
        test_suite = self.load_agent_tests(agent_name)
        return self.run_tests_from_suite(test_suite, environment, dry_run, write_reports)
    
    def _run_single_test(self, test_case: TestCase, request_builder: RequestBuilderService,
                        http_client: Optional[HttpClientService], dry_run: bool) -> TestResult:
        """Run a single test case.
        
        Args:
            test_case: Test case to execute
            request_builder: Service to build requests
            http_client: HTTP client for sending requests (None for dry run)
            dry_run: If True, don't actually send HTTP requests
            
        Returns:
            TestResult with execution outcome
        """
        start_time = time.time()
        logger.info(f"Running test: {test_case.test_name}")
        
        try:
            # Validate test case
            validation_errors = request_builder.validate_test_case(test_case)
            if validation_errors:
                return TestResult(
                    test_name=test_case.test_name,
                    status="error",
                    expected_response=test_case.expected_answer,
                    error_message=f"Validation failed: {'; '.join(validation_errors)}",
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            
            # Build HTTP request
            http_request = request_builder.build_http_request(test_case)
            logger.debug(f"Built HTTP request for {test_case.test_name}")
            
            # If dry run, just validate the request building
            if dry_run or not http_client:
                return TestResult(
                    test_name=test_case.test_name,
                    status="pass",  # Dry run success
                    expected_response=test_case.expected_answer,
                    actual_response="Dry run - request built successfully",
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            
            # Send HTTP request
            try:
                http_response = http_client.send_request(http_request)
            except Exception as http_error:
                # Handle HTTP errors (connection, auth, server errors, etc.)
                error_details = str(http_error)
                
                # Extract more details if it's an httpx error with response
                if hasattr(http_error, 'response') and http_error.response:
                    response = http_error.response
                    error_details = f"HTTP {response.status_code}: {response.text or 'No response body'}"
                
                return TestResult(
                    test_name=test_case.test_name,
                    status="error",
                    expected_response=test_case.expected_answer,
                    actual_response="",
                    error_message=f"HTTP request failed: {error_details}",
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            
            # Check for HTTP error status codes that should be treated as errors
            if http_response.status_code >= 400:
                error_body = http_response.text or "No response body"
                return TestResult(
                    test_name=test_case.test_name,
                    status="error",
                    expected_response=test_case.expected_answer,
                    actual_response=error_body,
                    error_message=f"HTTP {http_response.status_code} error: {error_body}",
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            
            # Handle response based on test type
            if test_case.test_name.lower() == "healthcheck":
                # For healthcheck, success is just getting a 2xx response
                if 200 <= http_response.status_code < 300:
                    return TestResult(
                        test_name=test_case.test_name,
                        status="pass",
                        expected_response=test_case.expected_answer,
                        actual_response=http_response.text or f"HTTP {http_response.status_code}",
                        execution_time_ms=(time.time() - start_time) * 1000,
                        comparison_method="healthcheck"
                    )
                else:
                    return TestResult(
                        test_name=test_case.test_name,
                        status="fail",
                        expected_response=test_case.expected_answer,
                        actual_response=f"HTTP {http_response.status_code}: {http_response.text}",
                        error_message=f"Healthcheck failed with status {http_response.status_code}",
                        execution_time_ms=(time.time() - start_time) * 1000,
                        comparison_method="healthcheck"
                    )
            
            # Parse agent response
            try:
                agent_response = AgentResponse.from_http_response(http_response)
            except Exception as e:
                return TestResult(
                    test_name=test_case.test_name,
                    status="error",
                    expected_response=test_case.expected_answer,
                    actual_response=http_response.text[:500] if http_response.text else "",
                    error_message=f"Failed to parse agent response: {e}",
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            
            # Compare expected vs actual response
            comparison_result = self.comparison_service.compare_responses(
                expected=test_case.expected_answer,
                actual=agent_response.answer,
                comparison_method=test_case.comparison_method,
                semantic_threshold=test_case.semantic_threshold,
                substring_words=test_case.required_words
            )
            
            # Determine test status
            status = "pass" if comparison_result.is_match else "fail"
            
            return TestResult(
                test_name=test_case.test_name,
                status=status,
                expected_response=test_case.expected_answer,
                actual_response=agent_response.answer,
                semantic_score=comparison_result.score,
                comparison_method=test_case.comparison_method,
                comparison_details=comparison_result.details,
                execution_time_ms=(time.time() - start_time) * 1000,
                tool_calls_made=agent_response.tool_calls_made
            )
            
        except Exception as e:
            logger.error(f"Test execution failed for {test_case.test_name}: {e}")
            return TestResult(
                test_name=test_case.test_name,
                status="error",
                expected_response=test_case.expected_answer,
                error_message=str(e),
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    def run_single_test(self, agent_name: str, test_name: str, environment: str = "dev", 
                       dry_run: bool = False) -> TestReport:
        """Run a single test case for an agent.
        
        Args:
            agent_name: Name of the agent to test
            test_name: Name of the specific test to run
            environment: Environment to test against
            dry_run: If True, don't send actual HTTP requests
            
        Returns:
            TestReport with single test result
        """
        start_time = time.time()
        logger.info(f"Running single test '{test_name}' for agent: {agent_name}")
        
        try:
            # Load single test
            test_case = self.test_service.load_test_case(
                Path(self.tests_dir) / agent_name / f"{test_name}.yaml"
            )
            if not test_case:
                test_case = self.test_service.load_test_case(
                    Path(self.tests_dir) / agent_name / f"{test_name}.yml"
                )
            
            if not test_case:
                return TestReport(
                    agent_name=agent_name,
                    total_tests=1,
                    passed=0,
                    failed=0,
                    errors=1,
                    results=[
                        TestResult(
                            test_name=test_name,
                            status="error",
                            error_message=f"Test file not found: {test_name}.yaml",
                            execution_time_ms=(time.time() - start_time) * 1000
                        )
                    ],
                    execution_time_total_ms=(time.time() - start_time) * 1000
                )
            
            # Load agent configuration
            agent_config = self.config_service.get_agent_config(agent_name, environment)
            
            # Initialize services
            request_builder = RequestBuilderService(agent_config, self.tests_dir)
            http_client = HttpClientService(agent_config) if not dry_run else None
            
            try:
                # Run the single test
                result = self._run_single_test(test_case, request_builder, http_client, dry_run)
                
                # Create test report with single result
                total_time_ms = (time.time() - start_time) * 1000
                passed = 1 if result.status == "pass" else 0
                failed = 1 if result.status == "fail" else 0
                errors = 1 if result.status == "error" else 0
                
                return TestReport(
                    agent_name=agent_name,
                    total_tests=1,
                    passed=passed,
                    failed=failed,
                    errors=errors,
                    results=[result],
                    execution_time_total_ms=total_time_ms
                )
                
            finally:
                if http_client:
                    http_client.close()
                    
        except Exception as e:
            logger.error(f"Single test execution failed: {e}")
            return TestReport(
                agent_name=agent_name,
                total_tests=1,
                passed=0,
                failed=0,
                errors=1,
                results=[
                    TestResult(
                        test_name=test_name,
                        status="error",
                        error_message=str(e),
                        execution_time_ms=(time.time() - start_time) * 1000
                    )
                ],
                execution_time_total_ms=(time.time() - start_time) * 1000
            )