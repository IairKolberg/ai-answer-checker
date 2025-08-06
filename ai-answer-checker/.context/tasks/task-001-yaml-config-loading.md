# Task: TASK-001 - YAML Configuration Loading

## Status
- [x] Planned
- [ ] Active
- [ ] Completed

## Description
Implement YAML configuration loading functionality that allows the CLI to read test configurations based on agent parameter.

## Objectives
- [ ] CLI accepts `--agent <name>` parameter
- [ ] Load configuration from `configs/<name>.yaml`
- [ ] Parse test cases and agent endpoints
- [ ] Validate configuration structure
- [ ] Handle missing or malformed config files

## Dependencies
None - this is the foundation task

## Implementation Steps
1. Create Pydantic models for configuration structure in `models.py`
2. Add YAML loading function in `runner.py`
3. Integrate with CLI argument parsing in `cli.py`
4. Add configuration validation and error handling
5. Create sample configuration file for testing

## Technical Considerations
- Use PyYAML for YAML parsing
- Pydantic for data validation and type safety
- Clear error messages for invalid configurations
- Support for environment variable substitution
- Configuration schema versioning

## Files to Modify
- `ai_answer_checker/models.py` - Add config models
- `ai_answer_checker/runner.py` - Add config loading
- `ai_answer_checker/cli.py` - Add agent parameter
- `configs/` - Create sample config files
- `tests/test_config.py` - Add tests

## Acceptance Criteria
- [ ] CLI accepts `--agent demo` parameter
- [ ] Loads `configs/demo.yaml` successfully
- [ ] Validates configuration structure
- [ ] Returns clear error for missing files
- [ ] Returns clear error for invalid YAML
- [ ] Configuration includes test cases and endpoints

## Python-Specific Requirements
- [ ] Follow PEP 8 style guide
- [ ] Add type hints for all functions
- [ ] Include comprehensive docstrings
- [ ] Handle file I/O exceptions properly
- [ ] Use pathlib for file operations