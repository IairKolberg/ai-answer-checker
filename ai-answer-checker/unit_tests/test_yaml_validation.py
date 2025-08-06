"""Tests for YAML file validation and parsing."""

import tempfile
import unittest
import yaml
from pathlib import Path
from pydantic import ValidationError

from ai_answer_checker.models import TestCase


class TestYAMLValidation(unittest.TestCase):
    
    def test_all_agent_yaml_files_are_valid(self):
        """Test that ALL YAML files in agent_tests/ directory are valid and parseable."""
        agent_tests_dir = Path("agent_tests")
        
        if not agent_tests_dir.exists():
            self.skipTest(f"Agent tests directory not found: {agent_tests_dir}")
        
        # Discover all YAML files recursively
        yaml_files = list(agent_tests_dir.rglob("*.yaml"))
        
        if not yaml_files:
            self.skipTest("No YAML files found in agent_tests directory")
        
        print(f"\n🔍 Validating {len(yaml_files)} YAML files in agent_tests/")
        
        invalid_files = {}  # Dictionary to group errors by file
        
        for yaml_file in yaml_files:
            try:
                print(f"  ✓ Validating: {yaml_file}")
                
                # First, load and analyze the raw YAML data for better error messages
                error_details = self._analyze_yaml_file(yaml_file)
                if error_details:
                    invalid_files[yaml_file] = error_details
                    continue
                
                # If no obvious issues, try to load with Pydantic for detailed validation
                test_case = TestCase.from_yaml_file(yaml_file)
                
                # Verify required fields are present and valid
                self.assertTrue(test_case.test_name, f"Missing test_name in {yaml_file}")
                self.assertTrue(test_case.user_input, f"Missing user_input in {yaml_file}")
                self.assertTrue(test_case.expected_answer, f"Missing expected_answer in {yaml_file}")
                self.assertTrue(0.0 <= test_case.semantic_threshold <= 1.0, f"Invalid semantic_threshold in {yaml_file}")
                self.assertIn(test_case.comparison_method, ["exact", "semantic", "substring"], f"Invalid comparison_method in {yaml_file}")
                
            except Exception as e:
                if yaml_file not in invalid_files:
                    invalid_files[yaml_file] = []
                invalid_files[yaml_file].append(str(e))
        
        # If any files failed validation, fail the test with details
        if invalid_files:
            error_lines = []
            for file_path, errors in invalid_files.items():
                error_lines.append(f"\n❌ {file_path}:")
                for error in errors:
                    error_lines.append(f"\n   • {error}")
            
            error_message = f"\n🚨 Found {len(invalid_files)} invalid YAML file{'s' if len(invalid_files) > 1 else ''}:" + "".join(error_lines)
            self.fail(error_message)
        
        print(f"✅ All {len(yaml_files)} YAML files are valid!")
    
    def _analyze_yaml_file(self, yaml_file: Path) -> list:
        """Analyze YAML file and return explicit error messages for common issues."""
        from ruamel.yaml import YAML
        
        try:
            yaml_loader = YAML(typ='safe')
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml_loader.load(f)
        except Exception as e:
            return [f"YAML syntax error: {str(e)}"]
        
        if data is None:
            return ["File is empty or contains only comments"]
        
        if not isinstance(data, dict):
            return ["YAML file must contain a dictionary/mapping, not a list or scalar value"]
        
        errors = []
        
        # Define required fields and their common typos
        field_checks = {
            'user_input': ['user_input2', 'userinput', 'input', 'user_query', 'query'],
            'expected_answer': ['expected_response', 'expected', 'answer', 'response', 'expected_result'],
            'semantic_threshold': ['threshold', 'semantic_score', 'similarity_threshold'],
            'comparison_method': ['method', 'comparison', 'compare_method', 'comparison_type']
        }
        
        # Check for missing required fields and suggest corrections
        required_fields = ['user_input', 'expected_answer']
        for required_field in required_fields:
            if required_field not in data:
                # Check if there's a similar field name (typo)
                suggestions = []
                for actual_field in data.keys():
                    if actual_field in field_checks.get(required_field, []):
                        suggestions.append(f"Found '{actual_field}' - did you mean '{required_field}'?")
                    elif actual_field.lower() == required_field.lower():
                        suggestions.append(f"Found '{actual_field}' - field names are case-sensitive, use '{required_field}'")
                
                if suggestions:
                    errors.append(f"Missing required field '{required_field}'. {suggestions[0]}")
                else:
                    errors.append(f"Missing required field '{required_field}'")
        
        # Check for invalid/unexpected fields
        # Note: test_name is now auto-derived from filename, so it's not expected in YAML
        valid_fields = {
            'variables', 'user_input', 'expected_answer', 
            'semantic_threshold', 'comparison_method', 'required_words', 'tool_stubs'
        }
        
        for field_name in data.keys():
            if field_name not in valid_fields:
                # Try to suggest the correct field name
                suggestion = self._suggest_field_name(field_name, valid_fields)
                if suggestion:
                    errors.append(f"Invalid field '{field_name}' - did you mean '{suggestion}'?")
                else:
                    errors.append(f"Invalid field '{field_name}' - valid fields are: {', '.join(sorted(valid_fields))}")
        
        # Check field value constraints
        if 'semantic_threshold' in data:
            threshold = data['semantic_threshold']
            if not isinstance(threshold, (int, float)) or not (0.0 <= threshold <= 1.0):
                errors.append(f"semantic_threshold must be a number between 0.0 and 1.0, got: {threshold}")
        
        if 'comparison_method' in data:
            method = data['comparison_method']
            valid_methods = ['exact', 'semantic', 'substring']
            if method not in valid_methods:
                errors.append(f"comparison_method must be one of {valid_methods}, got: '{method}'")
        
        return errors
    
    def _suggest_field_name(self, wrong_field: str, valid_fields: set) -> str:
        """Suggest the most likely correct field name for a typo."""
        wrong_lower = wrong_field.lower()
        
        # Common typo mappings
        typo_map = {
            'user_input2': 'user_input',
            'userinput': 'user_input',
            'testname': 'test_name',
            'expected_response': 'expected_answer',
            'method': 'comparison_method',
            'threshold': 'semantic_threshold'
        }
        
        if wrong_lower in typo_map:
            return typo_map[wrong_lower]
        
        # Find closest match by checking if any valid field contains the wrong field
        for valid_field in valid_fields:
            if wrong_lower in valid_field.lower() or valid_field.lower() in wrong_lower:
                return valid_field
        
        return None
    
    def test_load_valid_yaml_file(self):
        """Test loading a valid YAML test file."""
        # Create a valid test case
        valid_data = {
            "variables": {"employeeId": 123456},
            "user_input": "What is my current salary?",
            "expected_answer": "Your current annual salary is $75,000.",
            "semantic_threshold": 0.85,
            "comparison_method": "exact"
        }
        
        # Write to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(valid_data, f)
            temp_path = f.name
        
        try:
            test_case = TestCase.from_yaml_file(temp_path)
            # test_name should now be derived from filename
            self.assertEqual(test_case.test_name, Path(temp_path).stem)
            self.assertEqual(test_case.user_input, "What is my current salary?")
            self.assertEqual(test_case.semantic_threshold, 0.85)
            self.assertEqual(test_case.comparison_method, "exact")
        finally:
            Path(temp_path).unlink()
    
    def test_load_invalid_missing_required_fields(self):
        """Test that YAML with missing required fields fails validation."""
        # Missing required fields
        invalid_data = {
            "variables": {"employeeId": 123456},
            "semantic_threshold": 0.85
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(invalid_data, f)
            temp_path = f.name
        
        try:
            with self.assertRaises(ValidationError) as context:
                TestCase.from_yaml_file(temp_path)
            
            errors = context.exception.errors()
            error_fields = [error['loc'][0] for error in errors]
            # test_name is no longer required in YAML (derived from filename)
            self.assertIn('user_input', error_fields)
            self.assertIn('expected_answer', error_fields)
        finally:
            Path(temp_path).unlink()
    
    def test_load_invalid_semantic_threshold(self):
        """Test that invalid semantic threshold fails validation."""
        invalid_data = {
            "user_input": "What is my salary?",
            "expected_answer": "Your salary is $75,000.",
            "semantic_threshold": 1.5,  # Invalid - should be <= 1.0
            "comparison_method": "exact"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(invalid_data, f)
            temp_path = f.name
        
        try:
            with self.assertRaises(ValidationError):
                TestCase.from_yaml_file(temp_path)
        finally:
            Path(temp_path).unlink()
    
    def test_load_substring_comparison_with_required_words(self):
        """Test substring comparison method with required words."""
        substring_data = {
            "user_input": "How much tax did I pay?",
            "expected_answer": "Your tax breakdown includes Federal Income Tax and FICA.",
            "semantic_threshold": 0.85,
            "comparison_method": "substring",
            "required_words": ["Federal Income Tax", "FICA"]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(substring_data, f)
            temp_path = f.name
        
        try:
            test_case = TestCase.from_yaml_file(temp_path)
            self.assertEqual(test_case.comparison_method, "substring")
            self.assertEqual(test_case.required_words, ["Federal Income Tax", "FICA"])
        finally:
            Path(temp_path).unlink()
    
    def test_tool_stubs_validation(self):
        """Test tool stubs structure validation."""
        tool_stub_data = {
            "user_input": "Question with tools",
            "expected_answer": "Answer using tools",
            "semantic_threshold": 0.85,
            "comparison_method": "exact",
            "tool_stubs": {
                "paySlips": [
                    {
                        "request": {"payDetailsIds": [999999], "region": "US"},
                        "response_file": "payslips/999999.json"
                    }
                ]
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(tool_stub_data, f)
            temp_path = f.name
        
        try:
            test_case = TestCase.from_yaml_file(temp_path)
            self.assertIn("paySlips", test_case.tool_stubs)
            self.assertEqual(len(test_case.tool_stubs["paySlips"]), 1)
            self.assertEqual(test_case.tool_stubs["paySlips"][0].response_file, "payslips/999999.json")
        finally:
            Path(temp_path).unlink()


# Handle pytest import gracefully for different test runners
try:
    import pytest
except ImportError:
    # Mock pytest for unittest compatibility
    class MockPytest:
        @staticmethod
        def skip(reason):
            import unittest
            raise unittest.SkipTest(reason)
        
        @staticmethod
        def fail(message):
            raise AssertionError(message)
        
        @staticmethod
        def raises(exception_type):
            from contextlib import contextmanager
            @contextmanager
            def raises_context():
                try:
                    yield
                    raise AssertionError(f"Expected {exception_type.__name__} but no exception was raised")
                except exception_type:
                    pass
            return raises_context()
    
    pytest = MockPytest()