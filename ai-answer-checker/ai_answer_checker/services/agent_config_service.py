"""Service for managing AI agent configurations and endpoints."""

import os
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional
from ruamel.yaml import YAML

from ..models import AgentConfig


logger = logging.getLogger(__name__)


class AgentConfigService:
    """Service for loading and managing AI agent configurations."""
    
    def __init__(self, config_dir: str = "configs"):
        """Initialize the agent config service.
        
        Args:
            config_dir: Directory containing agent configuration files
        """
        self.config_dir = Path(config_dir)
        self._config_cache: Dict[str, AgentConfig] = {}
        self._yaml = YAML(typ='safe')
        
    def get_agent_config(self, agent_name: str, environment: str = "dev") -> AgentConfig:
        """Get configuration for a specific agent.
        
        Args:
            agent_name: Name of the agent
            environment: Environment (dev, staging, prod)
            
        Returns:
            AgentConfig for the specified agent and environment
            
        Raises:
            FileNotFoundError: If agent config file doesn't exist
            ValueError: If configuration is invalid
        """
        cache_key = f"{agent_name}:{environment}"
        
        # Return cached config if available
        if cache_key in self._config_cache:
            logger.debug(f"Using cached config for {cache_key}")
            return self._config_cache[cache_key]
        
        # Load configuration
        config = self._load_agent_config(agent_name, environment)
        
        # Cache and return
        self._config_cache[cache_key] = config
        logger.info(f"Loaded config for agent '{agent_name}' environment '{environment}'")
        return config
    
    def _load_agent_config(self, agent_name: str, environment: str) -> AgentConfig:
        """Load agent configuration from file or environment variables.
        
        Priority order:
        1. Environment variables (highest priority)
        2. Agent-specific config file (configs/{agent_name}.yaml)
        3. Default config file (configs/default.yaml)
        
        Raises:
            FileNotFoundError: If no configuration sources are found
        """
        config_data = {}
        config_sources_found = []
        
        # Load default config file if exists
        default_config_file = self.config_dir / "default.yaml"
        if default_config_file.exists():
            default_data = self._load_config_file(default_config_file)
            if environment in default_data:
                config_data.update(default_data[environment])
                config_sources_found.append(f"default.yaml[{environment}]")
        
        # Load agent-specific config file if exists
        agent_config_file = self.config_dir / f"{agent_name}.yaml"
        if agent_config_file.exists():
            agent_data = self._load_config_file(agent_config_file)
            if environment in agent_data:
                config_data.update(agent_data[environment])
                config_sources_found.append(f"{agent_name}.yaml[{environment}]")
        
        # Override with environment variables
        env_overrides = self._load_from_environment(agent_name, environment)
        if env_overrides:
            config_data.update(env_overrides)
            config_sources_found.append("environment variables")
        
        # Fail if no configuration sources found
        if not config_sources_found:
            available_files = [
                f for f in [default_config_file, agent_config_file] 
                if f.exists()
            ]
            if available_files:
                available_envs = []
                for config_file in available_files:
                    try:
                        data = self._load_config_file(config_file)
                        if data:
                            available_envs.extend(data.keys())
                    except:
                        pass
                error_msg = (
                    f"No configuration found for agent '{agent_name}' in environment '{environment}'. "
                    f"Available environments: {list(set(available_envs))} "
                    f"in files: {[f.name for f in available_files]}"
                )
            else:
                error_msg = (
                    f"No configuration found for agent '{agent_name}'. "
                    f"Expected config file: {agent_config_file} or {default_config_file}"
                )
            raise FileNotFoundError(error_msg)
        
        # Expand environment variables in config values
        config_data = self._expand_environment_variables(config_data)
        
        # Validate and create AgentConfig
        try:
            logger.info(f"Loaded configuration from: {', '.join(config_sources_found)}")
            return AgentConfig(**config_data)
        except Exception as e:
            raise ValueError(f"Invalid configuration for agent '{agent_name}': {e}")
    
    def _load_config_file(self, config_file: Path) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = self._yaml.load(f)
                return data or {}
        except Exception as e:
            logger.warning(f"Failed to load config file {config_file}: {e}")
            return {}
    

    
    def _load_from_environment(self, agent_name: str, environment: str) -> Dict:
        """Load configuration overrides from environment variables.
        
        Environment variable naming pattern:
        AI_AGENT_{AGENT_NAME}_{ENVIRONMENT}_{SETTING}
        
        Examples:
                - AI_AGENT_PAY_DETAILS_US_AGENT_DEV_BASE_URL
        - AI_AGENT_PAY_DETAILS_US_AGENT_PROD_TIMEOUT_SECONDS  
        - AI_AGENT_PAY_DETAILS_US_AGENT_DEV_AUTH_HEADER
        """
        env_overrides = {}
        prefix = f"AI_AGENT_{agent_name.upper()}_{environment.upper()}_"
        
        # Map of environment variable suffixes to config keys
        env_mappings = {
            "BASE_URL": "base_url",
            "TIMEOUT_SECONDS": ("timeout_seconds", int),
            "MAX_RETRIES": ("max_retries", int),
            "RETRY_DELAY_SECONDS": ("retry_delay_seconds", float),
            "AUTH_HEADER": "auth_header",
            "VERIFY_SSL": ("verify_ssl", lambda x: x.lower() == "true")
        }
        
        for env_suffix, config_key in env_mappings.items():
            env_var = f"{prefix}{env_suffix}"
            env_value = os.getenv(env_var)
            
            if env_value is not None:
                if isinstance(config_key, tuple):
                    # Apply type conversion
                    key, converter = config_key
                    try:
                        env_overrides[key] = converter(env_value)
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Invalid value for {env_var}: {env_value} ({e})")
                else:
                    env_overrides[config_key] = env_value
                
                logger.debug(f"Environment override: {env_var} = {env_value}")
        
        return env_overrides
    
    def _expand_environment_variables(self, config_data: Dict) -> Dict:
        """Expand environment variables in configuration values.
        
        Supports patterns like ${ENV_VAR} and ${ENV_VAR:default_value}
        """
        def expand_value(value):
            if isinstance(value, str):
                # Pattern: ${VAR_NAME} or ${VAR_NAME:default}
                pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'
                
                def replace_env_var(match):
                    var_name = match.group(1)
                    default_value = match.group(2) if match.group(2) is not None else ""
                    env_value = os.getenv(var_name, default_value)
                    logger.debug(f"Expanding ${{{var_name}}} = {env_value}")
                    return env_value
                
                return re.sub(pattern, replace_env_var, value)
            elif isinstance(value, dict):
                return {k: expand_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [expand_value(item) for item in value]
            else:
                return value
        
        return expand_value(config_data)
    
    def list_available_agents(self) -> List[str]:
        """List all agents that have configuration files."""
        if not self.config_dir.exists():
            logger.warning(f"Config directory not found: {self.config_dir}")
            return []
        
        agent_names = []
        for config_file in self.config_dir.glob("*.yaml"):
            if config_file.name != "default.yaml":
                agent_name = config_file.stem
                agent_names.append(agent_name)
        
        return sorted(agent_names)
    
    def clear_cache(self):
        """Clear the configuration cache."""
        self._config_cache.clear()
        logger.debug("Configuration cache cleared")
    
    def create_default_config_file(self, agent_name: str) -> Path:
        """Create a default configuration file for an agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Path to the created configuration file
        """
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        config_file = self.config_dir / f"{agent_name}.yaml"
        
        if config_file.exists():
            logger.warning(f"Config file already exists: {config_file}")
            return config_file
        
        # Create default configuration
        default_config = {
            "dev": {
                "agent_name": agent_name,
                "base_url": "http://localhost:8000",
                "endpoint_path": f"/agents/{agent_name}",
                "timeout_seconds": 30,
                "max_retries": 3,
                "retry_delay_seconds": 1.0,
                "headers": {
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                "verify_ssl": True
            },
            "staging": {
                "base_url": "https://staging-api.example.com",
                "endpoint_path": f"/agents/{agent_name}",
                "auth_header": "Bearer YOUR_STAGING_TOKEN"
            },
            "prod": {
                "base_url": "https://api.example.com",
                "endpoint_path": f"/agents/{agent_name}",
                "auth_header": "Bearer YOUR_PROD_TOKEN",
                "timeout_seconds": 60,
                "max_retries": 5
            }
        }
        
        # Write configuration file
        with open(config_file, 'w', encoding='utf-8') as f:
            self._yaml.dump(default_config, f)
        
        logger.info(f"Created default config file: {config_file}")
        return config_file