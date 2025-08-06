# AI Answer Checker Project Setup

## Project Overview
This is a minimal CLI regression runner for AI agent responses, inspired by enterprise AI platform architecture.

## Key Features
- CLI interface for running AI agent tests
- HTTP client for agent communication
- Response comparison and validation
- YAML-based test configuration
- FastAPI stub server for testing

## Python Environment Setup
1. **Python Version**: Requires Python 3.8+
2. **Virtual Environment**: 
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. **Dependencies Installation**:
   ```bash
   pip install -e .
   ```

## Project Structure
```
ai-answer-checker/
├── ai_answer_checker/           # Python package
│   ├── __init__.py             # Package entry point
│   ├── cli.py                  # Click CLI interface
│   ├── runner.py               # Test orchestration (TODO)
│   ├── stub.py                 # FastAPI stub server
│   ├── models.py               # Pydantic models for YAML configs
│   └── settings.py             # Configuration management
├── tests/                      # Test directory
├── .context/                   # AI context management
├── requirements.txt            # Dependencies
├── pyproject.toml             # Project metadata
└── README.md                  # Project documentation
```

## Development Guidelines
- Follow PEP 8 style guidelines
- Use type hints throughout the codebase
- Write comprehensive docstrings
- Maintain test coverage above 80%
- Use pytest for testing
- Implement proper error handling and logging

## Current Status
This is a scaffold project with basic structure in place. The main implementation work is still needed for the runner.py module.