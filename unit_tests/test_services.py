"""Tests for service layer functionality."""

import os
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch

from ai_answer_checker.services import TestConfigService, AgentConfigService, ResponseComparisonService
from ai_answer_checker.models import TestCase, AgentConfig


class TestTestConfigService:
    
    def test_discover_agents_in_directory(self):
        """Test agent discovery functionality."""
        # Create temporary test directory structure
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create agent directory with test file
            agent_dir = Path(temp_dir) / "test_agent"
            agent_dir.mkdir()
            
            test_data = {
                "test_name": "test",
                "user_input": "question",
                "expected_answer": "answer"
            }
            
            with open(agent_dir / "test.yaml", "w") as f:
                yaml.dump(test_data, f)
            
            service = TestConfigService(temp_dir)
            agents = service.discover_agents()
            
            assert "test_agent" in agents
    
    def test_load_agent_test_suite(self):
        """Test loading agent test suite."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create agent directory with test file
            agent_dir = Path(temp_dir) / "test_agent"
            agent_dir.mkdir()
            
            test_data = {
                "test_name": "valid_test",
                "user_input": "Test question",
                "expected_answer": "Test answer",
                "semantic_threshold": 0.85,
                "comparison_method": "exact"
            }
            
            with open(agent_dir / "valid_test.yaml", "w") as f:
                yaml.dump(test_data, f)
            
            service = TestConfigService(temp_dir)
            test_suite = service.load_agent_test_suite("test_agent")
            
            assert test_suite.agent_name == "test_agent"
            assert test_suite.total_tests == 1
            assert len(test_suite.test_cases) == 1
            assert test_suite.test_cases[0].test_name == "valid_test"
    
    def test_discover_empty_directory_returns_empty_list(self):
        """Test discovery in empty directory returns empty list."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = TestConfigService(temp_dir)
            agents = service.discover_agents()
            assert agents == []


class TestAgentConfigService:
    
    def test_get_agent_config_from_file(self):
        """Test getting agent configuration from file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create config file
            config_data = {
                "dev": {
                    "agent_name": "test_agent",
                    "base_url": "http://localhost:9493",
                    "endpoint_path": "/agent/test",
                    "timeout_seconds": 30
                }
            }
            
            config_file = Path(temp_dir) / "test_agent.yaml"
            with open(config_file, "w") as f:
                yaml.dump(config_data, f)
            
            service = AgentConfigService(temp_dir)
            config = service.get_agent_config("test_agent", "dev")
            
            assert config.agent_name == "test_agent"
            assert str(config.base_url) == "http://localhost:9493/"
            assert config.timeout_seconds == 30
    
    def test_environment_variable_expansion(self):
        """Test environment variable expansion in configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create config with environment variables
            config_data = {
                "prod": {
                    "agent_name": "env_agent",
                    "base_url": "${PROD_BASE_URL:http://localhost:8000}",
                    "endpoint_path": "/agent/env",
                    "auth_header": "${AUTH_TOKEN}",
                    "timeout_seconds": 60
                }
            }
            
            config_file = Path(temp_dir) / "env_agent.yaml"
            with open(config_file, "w") as f:
                yaml.dump(config_data, f)
            
            # Test with environment variables set
            env_vars = {
                "PROD_BASE_URL": "https://prod.example.com",
                "AUTH_TOKEN": "bearer-token-12345"
            }
            
            with patch.dict(os.environ, env_vars):
                service = AgentConfigService(temp_dir)
                config = service.get_agent_config("env_agent", "prod")
                
                assert str(config.base_url) == "https://prod.example.com/"
                assert getattr(config, 'auth_header', None) == "bearer-token-12345"
    
    def test_list_available_agents(self):
        """Test listing available agents."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create multiple config files
            agents = ["agent1", "agent2", "agent3"]
            for agent in agents:
                config_data = {
                    "agent_name": agent,
                    "dev": {"base_url": "http://localhost:8000"}
                }
                config_file = Path(temp_dir) / f"{agent}.yaml"
                with open(config_file, "w") as f:
                    yaml.dump(config_data, f)
            
            service = AgentConfigService(temp_dir)
            available_agents = service.list_available_agents()
            
            for agent in agents:
                assert agent in available_agents


class TestResponseComparisonService:
    
    def test_exact_comparison_matching_responses(self):
        """Test exact comparison with matching responses."""
        service = ResponseComparisonService()
        
        actual = "Your salary is $75,000 per year."
        expected = "Your salary is $75,000 per year."
        
        result = service.compare_responses(
            actual, expected, comparison_method="exact"
        )
        
        assert result.is_match is True
        assert result.score == 1.0
        assert result.method == "exact"
    
    def test_exact_comparison_non_matching_responses(self):
        """Test exact comparison with non-matching responses."""
        service = ResponseComparisonService()
        
        actual = "Your salary is $75,000 per year."
        expected = "Your salary is $80,000 per year."
        
        result = service.compare_responses(
            actual, expected, comparison_method="exact"
        )
        
        assert result.is_match is False
        assert result.score == 0.0
        assert result.method == "exact"
    
    def test_substring_comparison_all_words_found(self):
        """Test substring comparison with all required words found."""
        service = ResponseComparisonService()
        
        actual = "Your tax breakdown: Federal Income Tax $2,640, FICA $960, Medicare $225"
        required_words = ["Federal Income Tax", "$2,640", "FICA", "Medicare"]
        
        result = service.compare_responses(
            actual, "", comparison_method="substring", substring_words=required_words
        )
        
        assert result.is_match is True
        assert result.score == 1.0
        assert result.method == "substring"
    
    def test_substring_comparison_partial_words_found(self):
        """Test substring comparison with some required words missing."""
        service = ResponseComparisonService()
        
        actual = "Your tax breakdown: Federal Income Tax $2,640, FICA $960"
        required_words = ["Federal Income Tax", "$2,640", "FICA", "Medicare", "State Tax"]
        
        result = service.compare_responses(
            actual, "", comparison_method="substring", substring_words=required_words
        )
        
        assert result.is_match is False
        assert result.score == 0.6  # 3 out of 5 words found
        assert result.method == "substring"
    
    def test_semantic_comparison_uses_fuzzy_matching(self):
        """Test semantic comparison (currently uses fuzzy matching)."""
        service = ResponseComparisonService()
        
        actual = "Your annual salary is seventy-five thousand dollars."
        expected = "Your yearly pay is $75,000."
        
        result = service.compare_responses(
            actual, expected, comparison_method="semantic", semantic_threshold=0.3
        )
        
        assert result.method == "semantic"
        assert 0.0 <= result.score <= 1.0
        # Score will vary based on fuzzy matching algorithm
    
    def test_invalid_comparison_method_handles_gracefully(self):
        """Test that invalid comparison method is handled gracefully."""
        service = ResponseComparisonService()
        
        result = service.compare_responses(
            "actual", "expected", comparison_method="invalid_method"
        )
        
        assert result.is_match is False
        assert result.score == 0.0
        assert result.error_message is not None
        assert "Unknown comparison method" in result.error_message