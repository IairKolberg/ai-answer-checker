"""Tests for Pydantic model validation."""

import unittest
from contextlib import contextmanager
from pydantic import ValidationError
from ai_answer_checker.models import TestCase, AgentConfig, TestResult, TestReport


class TestTestCaseModel(unittest.TestCase):
    
    def test_valid_test_case_creation(self):
        """Test creating a valid test case."""
        test_case = TestCase(
            test_name="sample_test",  # Can still be set manually
            variables={"employeeId": 123456},
            user_input="What is my salary?",
            expected_answer="Your salary is $75,000.",
            semantic_threshold=0.85,
            comparison_method="exact"
        )
        
        self.assertEqual(test_case.test_name, "sample_test")
        self.assertEqual(test_case.user_input, "What is my salary?")
        self.assertEqual(test_case.semantic_threshold, 0.85)
        self.assertEqual(test_case.comparison_method, "exact")
        self.assertEqual(test_case.variables, {"employeeId": 123456})
    
    def test_missing_required_fields_raises_validation_error(self):
        """Test that missing required fields raise ValidationError."""
        with self.assertRaises(ValidationError) as context:
            TestCase()  # Missing user_input, expected_answer (test_name is now optional)
        
        errors = context.exception.errors()
        error_fields = [error['loc'][0] for error in errors]
        self.assertIn('user_input', error_fields)
        self.assertIn('expected_answer', error_fields)
    
    def test_invalid_semantic_threshold_raises_validation_error(self):
        """Test that invalid semantic threshold raises ValidationError."""
        with self.assertRaises(ValidationError):
            TestCase(
                user_input="question",
                expected_answer="answer",
                semantic_threshold=1.5  # Invalid - too high
            )
        
        with self.assertRaises(ValidationError):
            TestCase(
                user_input="question",
                expected_answer="answer",
                semantic_threshold=-0.1  # Invalid - too low
            )
    
    def test_default_values_applied_correctly(self):
        """Test that default values are applied correctly."""
        test_case = TestCase(
            user_input="question", 
            expected_answer="answer"
        )
        
        self.assertEqual(test_case.test_name, "")  # Default empty string
        self.assertEqual(test_case.semantic_threshold, 0.85)  # Default
        self.assertEqual(test_case.comparison_method, "semantic")  # Default
        self.assertEqual(test_case.variables, {})  # Default
    
    def test_substring_method_with_required_words(self):
        """Test substring comparison method with required words."""
        test_case = TestCase(
            user_input="question",
            expected_answer="answer",
            comparison_method="substring",
            required_words=["word1", "word2"]
        )
        
        self.assertEqual(test_case.comparison_method, "substring")
        self.assertEqual(test_case.required_words, ["word1", "word2"])


class TestAgentConfigModel(unittest.TestCase):
    
    def test_valid_agent_config_creation(self):
        """Test creating a valid agent configuration."""
        config = AgentConfig(
            agent_name="test_agent",
            base_url="http://localhost:9493",
            endpoint_path="/agent/test",
            timeout_seconds=30,
            max_retries=3
        )
        
        self.assertEqual(config.agent_name, "test_agent")
        self.assertEqual(str(config.base_url), "http://localhost:9493/")  # Pydantic adds trailing slash
        self.assertEqual(config.timeout_seconds, 30)
        self.assertEqual(config.max_retries, 3)
    
    def test_missing_required_fields_raises_validation_error(self):
        """Test that missing required fields raise ValidationError."""
        with self.assertRaises(ValidationError) as context:
            AgentConfig()  # Missing all required fields
        
        errors = context.exception.errors()
        error_fields = [error['loc'][0] for error in errors]
        self.assertIn('agent_name', error_fields)
        self.assertIn('base_url', error_fields)
    
    def test_invalid_timeout_raises_validation_error(self):
        """Test that invalid timeout raises ValidationError."""
        with self.assertRaises(ValidationError):
            AgentConfig(
                agent_name="test",
                base_url="http://localhost:8000",
                timeout_seconds=-1  # Invalid
            )
    
    def test_default_values_applied_correctly(self):
        """Test that default values are applied correctly."""
        config = AgentConfig(
            agent_name="test",
            base_url="http://localhost:8000",
            endpoint_path="/agent/test"
        )
        
        self.assertEqual(config.timeout_seconds, 30)  # Default
        self.assertEqual(config.max_retries, 3)  # Default
        self.assertTrue(config.verify_ssl)  # Default


class TestTestResultModel(unittest.TestCase):
    
    def test_valid_test_result_creation(self):
        """Test creating a valid test result."""
        result = TestResult(
            test_name="test",
            status="pass",
            expected_response="expected",
            actual_response="actual",
            execution_time_ms=100.5
        )
        
        self.assertEqual(result.test_name, "test")
        self.assertEqual(result.status, "pass")
        self.assertEqual(result.execution_time_ms, 100.5)
    
    def test_optional_fields_work_correctly(self):
        """Test that optional fields work correctly."""
        result = TestResult(
            test_name="test",
            status="pass",
            expected_response="expected"
        )
        
        self.assertIsNone(result.actual_response)
        self.assertIsNone(result.semantic_score)
        self.assertIsNone(result.error_message)


class TestTestReportModel(unittest.TestCase):
    
    def test_valid_test_report_creation(self):
        """Test creating a valid test report."""
        results = [
            TestResult(test_name="test1", status="pass", expected_response="exp1"),
            TestResult(test_name="test2", status="fail", expected_response="exp2")
        ]
        
        report = TestReport(
            agent_name="test_agent",
            total_tests=2,
            passed=1,
            failed=1,
            errors=0,
            results=results
        )
        
        self.assertEqual(report.agent_name, "test_agent")
        self.assertEqual(report.total_tests, 2)
        self.assertEqual(report.passed, 1)
        self.assertEqual(report.failed, 1)
    
    def test_calculated_properties_work_correctly(self):
        """Test that calculated properties work correctly."""
        results = [
            TestResult(test_name="test1", status="pass", expected_response="exp1"),
            TestResult(test_name="test2", status="pass", expected_response="exp2"),
            TestResult(test_name="test3", status="fail", expected_response="exp3"),
            TestResult(test_name="test4", status="error", expected_response="exp4")
        ]
        
        report = TestReport(
            agent_name="test_agent",
            total_tests=4,
            passed=2,
            failed=1,
            errors=1,
            results=results
        )
        
        self.assertEqual(report.pass_percentage, 50.0)  # 2/4 * 100
        self.assertEqual(report.fail_percentage, 25.0)  # 1/4 * 100
        self.assertEqual(report.error_percentage, 25.0)  # 1/4 * 100
        self.assertEqual(report.overall_status, "ERROR")  # Has errors