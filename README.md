# AI Answer Checker

A powerful regression testing framework for AI agents that validates responses against expected outputs using multiple comparison methods.

## 🎯 What It Does

The AI Answer Checker helps you:
- **Test AI agent responses** automatically against expected outputs
- **Prevent regressions** when updating AI models or prompts
- **Validate response quality** using semantic, exact, and substring matching
- **Generate detailed reports** in CSV format for analysis
- **Integrate with CI/CD** pipelines for automated testing
- **Mock external dependencies** using tool stubs for isolated testing

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Virtual environment (recommended)

### Installation

1. **Clone the repository:**
```bash
git clone <your-repo-url>
cd ai-answer-checker
```

2. **Create virtual environment:**
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies:**
```bash
# Recommended: install the package (and its dependencies) in editable mode
pip install -e .

# Optional: install dev/test extras
pip install -r requirements.txt
```

4. **Verify installation:**
```bash
python3 -m ai_answer_checker --help
```

5. **Run unit tests:**
```bash
python -m pytest unit_tests/ -v
```

## 📖 Basic Usage

### List Available Agents
```bash
python3 -m ai_answer_checker --list-agents
```

### Run All Tests
```bash
# Test all tests for an agent
python3 -m ai_answer_checker --agent pay-details-us-agent
```

### Run Single Test
```bash
# Test a specific test case
python3 -m ai_answer_checker --agent pay-details-us-agent --test base_salary_march_2025
```

### Run Tests (Dry Run)
```bash
# Validate configurations without making HTTP requests
python3 -m ai_answer_checker --agent pay-details-us-agent --dry-run

# Dry run a single test
python3 -m ai_answer_checker --agent pay-details-us-agent --test healthcheck --dry-run
```

### JSON Output (for CI/CD)
```bash
# Machine-readable output
python3 -m ai_answer_checker --agent pay-details-us-agent --format json
```

## 🛠️ CLI Options

### Required Options
- `--agent AGENT_NAME` - Name of the agent to test (e.g., 'pay-details-us-agent')

### Test Selection
- `--test TEST_NAME` - Run only a specific test file (e.g., 'base_salary_march_2025')
  - Test name should be the filename without `.yaml` extension
  - Example: `--test why_net_lower` runs `agent_tests/pay-details-us-agent/why_net_lower.yaml`

### Environment & Execution
- `--dry-run` - Validate configurations without sending HTTP requests

### Stub Service Control
- `--keep-stubs` - Keep stub service running after tests complete (for manual testing)
- `--no-stubs` - Skip stub service entirely - test against real services (integration testing)

### Output & Formatting
- `--format FORMAT` - Output format (default: 'console')
  - `console` - Human-readable console output
  - `json` - Machine-readable JSON output for CI/CD
- `--out TEXT` - Output file path for test results (optional)

### Utility
- `--list-agents` - List all available agents
- `--help` - Show help message

## 🎯 Usage Examples

### Running All Tests
```bash
# Run all tests for an agent
python3 -m ai_answer_checker --agent pay-details-us-agent
```

### Running Single Tests
```bash
# Run a specific test
python3 -m ai_answer_checker --agent pay-details-us-agent --test base_salary_march_2025

# Run single test with dry-run
python3 -m ai_answer_checker --agent pay-details-us-agent --test healthcheck --dry-run

# Run single test with JSON output
python3 -m ai_answer_checker --agent pay-details-us-agent --test why_net_lower --format json
```

### Validation and Debugging
```bash
# Dry run to see what requests would be sent
python3 -m ai_answer_checker --agent pay-details-us-agent --dry-run

# List available agents
python3 -m ai_answer_checker --list-agents
```

### Stub Service Management
```bash
# Keep stub service running for manual testing with Postman/curl
python3 -m ai_answer_checker --agent pay-details-us-agent --test march_deduction --keep-stubs

# Test against real services (no mocking) - useful for GitPod/integration testing
python3 -m ai_answer_checker --agent pay-details-us-agent --test march_deduction --no-stubs
```

## 📁 Project Structure

```
ai-answer-checker/
├── ai_answer_checker/              # Main package
│   ├── __init__.py
│   ├── __main__.py                # Package entry point
│   ├── cli.py                     # Command-line interface
│   ├── models.py                  # Data models (Pydantic)
│   ├── runner.py                  # Test execution engine
│   └── services/                  # Business logic services
│       ├── __init__.py
│       ├── agent_config_service.py        # Agent config loading
│       ├── http_client_service.py         # HTTP requests & retries
│       ├── report_writer_service.py       # CSV report generation
│       ├── request_builder_service.py     # Test request building
│       ├── response_comparison_service.py # Answer comparison
│       ├── semantic_providers.py          # Local semantic models
│       ├── stub_service.py               # Mock HTTP server
│       └── test_config_service.py        # YAML test loading
├── agent_tests/                   # Test definitions (hardcoded directory)
│   └── pay-details-us-agent/     # Agent-specific tests
│       ├── agent-services.yaml   # Agent-level stubs (MCP services)
│       ├── base_salary_march_2025.yaml    # Basic test case
│       ├── healthcheck.yaml      # Connectivity test  
│       ├── march_deduction.yaml  # Tool-enabled test
│       ├── tax_paid.yaml         # Another tool test
│       └── stubs/                # Mock response data
│           ├── mcp/              # MCP service definitions
│           │   └── payDetailsMCP.json
│           ├── payslips/         # Tool response mocks
│           │   ├── 999998.json
│           │   └── 999999.json
│           └── paySlipsSummary/  # Summary tool mocks
│               └── 999999.json
├── configs/                      # Agent configurations (hardcoded directory)
│   └── pay-details-us-agent.yaml  # Agent config (dev environment only)
├── reports/                      # Generated test reports (hardcoded directory)
├── unit_tests/                   # Unit tests
├── .vscode/                      # VS Code debug configurations
│   └── launch.json              # Pre-configured debug setups
├── pyproject.toml               # Package metadata
├── requirements.txt             # Dependencies
└── README.md                    # This file
```

## ⚙️ Configuration

### Agent Configuration

Create `configs/{agent_name}.yaml` (only `dev` environment is used):

```yaml
agent_name: pay-details-us-agent

# Development environment (hardcoded - only environment used)
dev:
  base_url: "http://localhost:9007"
  endpoint_path: "/agent/pay-details-us-agent-v1"  # Required field
  timeout_seconds: 30
  max_retries: 3
  headers:
    Content-Type: "application/json"
    Accept: "application/json"
```

**Note:** The system only uses the `dev` environment. All requests go to the configured `base_url` + `endpoint_path`.

### Environment Variables

You can use environment variables in configs:

```bash
# Example: Set base URL dynamically
export DEV_AI_URL="http://localhost:9007"

# Then in your config:
# dev:
#   base_url: "${DEV_AI_URL:http://localhost:9007}"
```

## 📝 Test File Format

Create test files in `agent_tests/{agent_name}/`:

### Basic Test Example
```yaml
# agent_tests/pay-details-us-agent/simple_question.yaml
# Note: test_name is automatically derived from filename (simple_question)
variables:
  employeeId: 123456
user_input: "What is my current salary?"
expected_answer: "Your current annual salary is $75,000."
semantic_threshold: 0.85
comparison_method: exact  # exact, semantic, or substring
```

### Tool-Enabled Test Example
```yaml
# agent_tests/pay-details-us-agent/march_deduction.yaml
# Note: test_name is automatically derived from filename (march_deduction)
variables:
  payDetailsId: 999999
  employeeId: "123456"
user_input: "on March 7 2025 I had a deduction, what is it?"
expected_answer: |
  On March 7, 2025, you had a deduction for health insurance
  in the amount of $125.00.
semantic_threshold: 0.8
comparison_method: semantic
tool_stubs:
  getPayDetails:
    - request:
        payDetailsId: 999999
        employeeId: "123456"
      response_file: payslips/999999.json
  getPayDetailsSummary:
    - request:
        employeeId: "123456"
      response_file: paySlipsSummary/999999.json
```

### Healthcheck Test Example
```yaml
# agent_tests/pay-details-us-agent/healthcheck.yaml
# Note: test_name is automatically derived from filename (healthcheck)
variables: {}
user_input: "ping"
expected_answer: "pong"
semantic_threshold: 0.85
comparison_method: exact
```



## 🔧 Tool Stubs (Mocking)

Tool stubs allow you to mock external API responses for isolated testing. The system supports both test-specific stubs and agent-level stubs.

### Agent-Level Stubs

Create `agent_tests/{agent_name}/agent-services.yaml` for stubs shared across all tests:

```yaml
# agent_tests/pay-details-us-agent/agent-services.yaml
agent_stubs:
  api/mcp/service/payDetailsMCP:
    - request: {}
      response_file: mcp/payDetailsMCP.json
```

### Directory Structure
```
agent_tests/pay-details-us-agent/
├── agent-services.yaml     # Agent-level stubs (MCP service definitions)
├── march_deduction.yaml    # Test file with tool_stubs
└── stubs/
    ├── mcp/                # MCP service definitions
    │   └── payDetailsMCP.json
    ├── payslips/           # Tool response mocks
    │   ├── 999998.json
    │   └── 999999.json
    └── paySlipsSummary/    # Summary tool mocks
        └── 999999.json
```

### Stub Response File Example
```json
// agent_tests/pay-details-us-agent/stubs/payslips/999999.json
{
  "payDetailsId": 999999,
  "employeeId": 123456,
  "grossPay": 6250.00,
  "netPay": 4750.00,
  "deductions": {
    "federalTax": 875.00,
    "stateTax": 312.50,
    "fica": 387.50,
    "medicare": 90.63
  }
}
```

## 📊 Comparison Methods

### 1. Exact Match
- **When to use:** Testing deterministic responses
- **How it works:** Character-by-character comparison
```yaml
comparison_method: exact
```

### 2. Semantic Comparison
- **When to use:** Testing meaning/intent of responses
- **How it works:** Advanced embeddings-based similarity using SentenceTransformers
- **Model:** Uses `all-MiniLM-L6-v2` for computing semantic embeddings
- **Accuracy:** 6x more accurate than simple text matching for semantic understanding
```yaml
comparison_method: semantic
semantic_threshold: 0.85  # 85% similarity required (0.0-1.0)
```

**Semantic Provider Features:**
- **🔒 Security-First:** Local-only operation with no external downloads
- **🧠 Advanced Embeddings:** Uses state-of-the-art SentenceTransformers models
- **⚡ High Performance:** 6x more accurate than simple text matching
- **🛡️ Graceful Fallback:** Falls back to simple text matching if models unavailable
- **📱 Easy Setup:** One-time local model download, then fully offline

#### Setting Up Local Models (Security-Compliant)

For security-sensitive environments, the system requires local models and **does not download** from external sources. Here's how to set up local models:

**1. Download Model Locally (one-time setup):**
```python
# download_model.py - Run this once to set up local model
from sentence_transformers import SentenceTransformer
from pathlib import Path

# Download and save model locally
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
local_path = Path("/path/to/your/models/all-MiniLM-L6-v2")
model.save(str(local_path))
print(f"Model saved to: {local_path}")
```

**2. Configure Local-Only Provider:**
```python
# Custom semantic provider configuration
from ai_answer_checker.services.semantic_providers import SemanticProviderFactory

# Use local model only (no external downloads)
config = {
    "type": "sentence_transformers",
    "model_path": "/path/to/your/models/all-MiniLM-L6-v2"
}

# Fallback to simple text matching if model unavailable
config = {"type": "fallback"}

provider = SemanticProviderFactory.create_provider(config)
```

**3. Verify Local-Only Operation:**
The system will log `Successfully loaded local SentenceTransformer model` and **never attempt external downloads**.

### 3. Substring Matching
- **When to use:** Testing for presence of specific keywords/values
- **How it works:** Checks if all required words are present
```yaml
comparison_method: substring
required_words: ["Federal Income Tax", "$2,640.00", "total"]
```

## 📈 Reports

### CSV Report Format
Generated as `reports/{agent-slug}_results_{timestamp}.csv`:

```csv
test_name,test_type,status,similarity,error,expected_answer,actual_answer
OVERALL_SUMMARY_pay_details_us_agent,summary,passed,100.0%,passed: 3/3,,
healthcheck,exact,pass,1.000,,Service is healthy,HTTP 200 OK
why_net_lower,semantic,pass,0.923,,Your net pay is lower due to...,Your net pay decreased because...
yearly_tax_totals,substring,pass,1.000,,Federal Income Tax: $2640...,Based on your YTD records: Federal Income Tax: $2640...
```

**CSV Columns:**
- `test_name`: Name of the test (derived from filename)
- `test_type`: Comparison method used (exact, semantic, substring, healthcheck)
- `status`: Test result (pass, fail, error)
- `similarity`: Similarity score for semantic comparisons (0.0-1.0)
- `error`: Error message if the test failed to execute
- `expected_answer`: Expected response from test case (truncated to 200 characters)
- `actual_answer`: Actual response from AI agent (truncated to 200 characters)

### JSON Output Example
```json
{
  "agent": "pay-details-us-agent",
  "environment": "dev",
  "success_rate": 100.0,
  "threshold_met": true,
  "status": "passed",
  "total_tests": 3,
  "passed": 3,
  "failed": 0,
  "errors": 0,
  "execution_time_ms": 1250.5,
  "tests": [
    {
      "name": "healthcheck",
      "status": "pass",
      "comparison_method": "exact",
      "score": 1.0,
      "error": null
    }
  ]
}
```

## 🔄 CI/CD Integration

### GitHub Actions Example
```yaml
# .github/workflows/ai-regression-tests.yml
name: AI Regression Tests
on: [push, pull_request]

jobs:
  test-ai-agents:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          pip install click httpx pydantic ruamel.yaml
      
      - name: Run AI regression tests
        env:
          STAGING_AI_URL: ${{ secrets.STAGING_AI_URL }}
          STAGING_AUTH_TOKEN: ${{ secrets.STAGING_AUTH_TOKEN }}
        run: |
          python -m ai_answer_checker \
            --agent pay-details-us-agent \
            --format json
      
      - name: Upload test reports
        uses: actions/upload-artifact@v3
        with:
          name: ai-test-reports
          path: reports/*.csv
```

## 🔧 Tool Stub Service

The AI Answer Checker includes an integrated HTTP stub service that mocks tool endpoints for isolated testing:

```bash
# The stub service automatically runs on port 9876 and:
# 1. Loads mock data from JSON files
# 2. Starts HTTP server with tool endpoints  
# 3. Serves mock responses to AI agent tool calls
# 4. Stops cleanly after tests complete

# Keep stub service running for manual testing
python3 -m ai_answer_checker --agent pay-details-us-agent --keep-stubs

# Skip stub service entirely (test against real services)
python3 -m ai_answer_checker --agent pay-details-us-agent --no-stubs
```

### Stub Service Architecture

```
┌─────────────────────────────────────┐    ┌─────────────────────────────┐
│        AI Answer Checker            │    │         AI Agent            │
│         (Test Runner)               │    │                             │
│                                     │    │                             │
│  1. Start stub HTTP service         │    │                             │
│  2. Send test request          ────────→ │  3. Process request         │
│                                     │    │  4. Need tool data?         │
│  6. Return mock JSON data      ←─────────  5. GET /paySlips?...        │
│  7. Receive final response     ←─────────  6. Return AI response       │
│  8. Compare vs expected answer      │    │                             │
└─────────────────────────────────────┘    └─────────────────────────────┘
```

### Stub Service URLs

When running, the stub service provides these endpoints:

```bash
# Health check
http://localhost:9876/health

# Tool endpoints (automatically generated)
http://localhost:9876/getPayDetails
http://localhost:9876/getPayDetailsSummary

# MCP service definitions
http://localhost:9876/api/mcp/service/payDetailsMCP
```

**Endpoint Types:**
- **`GET /health`** - Health check for the stub service
- **`GET /{tool_name}?{params}`** - GET-based tool calls
- **`POST /{tool_name}`** - POST-based tool calls with JSON body

Example tool calls:
```bash
# Tool calls to stub service
curl "http://localhost:9876/getPayDetails?payDetailsId=999999&employeeId=123456"
curl "http://localhost:9876/getPayDetailsSummary?employeeId=123456"

# Returns JSON from agent_tests/pay-details-us-agent/stubs/{tool_name}/{response_file}
```

### Deployment Gate Script
```bash
#!/bin/bash
echo "🧪 Running AI regression tests before deployment..."

python -m ai_answer_checker \
  --agent pay-details-us-agent \
  --format json > test-results.json

if [ $? -eq 0 ]; then
    echo "✅ All tests passed - proceeding with deployment"
    ./deploy-to-production.sh
else
    echo "❌ Tests failed - deployment blocked"
    cat test-results.json
    exit 1
fi
```

### Jenkins Pipeline Example
```groovy
pipeline {
    agent any
    
    environment {
        PROD_AI_URL = credentials('prod-ai-url')
        PROD_AUTH_TOKEN = credentials('prod-auth-token')
    }
    
    stages {
        stage('AI Regression Tests') {
            steps {
                sh '''
                    python -m ai_answer_checker \
                        --agent pay-details-us-agent \
                        --format json
                '''
            }
        }
        
        stage('Deploy') {
            when {
                expression { 
                    return currentBuild.currentResult == 'SUCCESS' 
                }
            }
            steps {
                sh './deploy.sh'
            }
        }
    }
    
    post {
        always {
            archiveArtifacts artifacts: 'reports/*.csv', fingerprint: true
        }
        failure {
            emailext (
                subject: "AI Tests Failed: ${env.JOB_NAME} - ${env.BUILD_NUMBER}",
                body: "AI regression tests failed. Check the build for details.",
                to: "${env.CHANGE_AUTHOR_EMAIL}"
            )
        }
    }
}
```

## 🧪 Testing

### Testing Overview

The project has two separate testing systems:

#### Unit Tests (`unit_tests/`)
Framework validation tests that ensure the ai-answer-checker code works correctly:
- **YAML file parsing and validation** - Ensures test files are correctly formatted
- **Model validation** - Tests Pydantic model constraints and defaults  
- **Service functionality** - Tests core business logic including configuration loading

#### Agent Tests (`agent_tests/`)
YAML test scenarios that define expected AI agent behavior:
- **Agent-specific test cases** - Define expected responses for different prompts
- **Tool stubs** - Mock external API responses for isolated testing
- **Multiple comparison methods** - Support exact, semantic, and substring matching

#### Running Tests

```bash
# Run all unit tests (includes integration tests)
python -m unittest discover -s unit_tests -v

# Run specific test categories
python -m unittest unit_tests.test_yaml_validation -v        # YAML validation tests
python -m unittest unit_tests.test_models -v                # Model validation tests
python -m unittest unit_tests.test_stub_service_integration -v  # HTTP stub service tests

# Alternative: use pytest if installed
python -m pytest unit_tests/ -v
python -m pytest unit_tests/ --cov=ai_answer_checker --cov-report=html
```

#### Test Structure

```
unit_tests/                                # Framework unit tests
├── test_models.py                        # Model validation tests
├── test_yaml_validation.py               # YAML parsing tests
└── test_stub_service_integration.py      # HTTP stub service integration tests

agent_tests/                               # AI agent test scenarios
└── pay-details-us-agent/                     # Agent-specific test files
    ├── base_salary_march_2025.yaml
    ├── healthcheck.yaml
    ├── why_net_lower.yaml
    └── yearly_tax_totals.yaml
```

#### Writing New Tests

When adding new YAML test files, the unit tests will automatically validate:
- Required fields are present (`user_input`, `expected_answer`)
- Semantic threshold is between 0.0 and 1.0
- Comparison method is valid (`exact`, `semantic`, `substring`)
- Tool stubs reference existing files
- YAML syntax is valid

Example unit test validation:
```python
# unit_tests/test_my_new_feature.py
import tempfile
import yaml
from ai_answer_checker.models import TestCase

class TestMyNewFeature:
    def test_new_yaml_file_validation(self):
        """Test that new YAML file is valid."""
        test_data = {
            "test_name": "expected_name",
            "user_input": "Test question",
            "expected_answer": "Test answer",
            "semantic_threshold": 0.85,
            "comparison_method": "exact"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_data, f)
            temp_path = f.name
        
        test_case = TestCase.from_yaml_file(temp_path)
        assert test_case.test_name == "expected_name"
        assert 0.0 <= test_case.semantic_threshold <= 1.0
        assert test_case.comparison_method in ["exact", "semantic", "substring"]
```

Example agent test file:
```yaml
# agent_tests/my_agent/new_test.yaml
test_name: my_new_test
variables:
  employeeId: 123456
user_input: "What is my salary?"
expected_answer: "Your salary is $75,000."
semantic_threshold: 0.85
comparison_method: exact
tool_stubs:
  payroll:
    - request:
        employee_id: 123456
      response_file: payroll/salary_data.json
```

## 🐛 Debugging

### Visual Debugging (VS Code/Cursor)

The project includes pre-configured debug configurations in `.vscode/launch.json`:

1. **🔴 Debug Single Test: march_deduction** - Debug with stubs (mocked dependencies)
2. **🌐 Debug Single Test: march_deduction (No Stubs)** - Debug against real services  
3. **Debug AI Answer Checker (All Tests)** - Debug all tests with stubs

**To debug:**
1. Set breakpoints by clicking in the left margin  
2. Press **F5** or go to **Run and Debug** panel
3. Select your desired configuration
4. Use debug console to inspect variables

**Pro tip:** Use the "No Stubs" configuration for GitPod or when you want to debug real HTTP interactions!

### Command Line Debugging
```bash
# Enable verbose logging
export PYTHONPATH=.
python -m ai_answer_checker --agent pay-details-us-agent --dry-run

# Check exit codes
echo $?  # 0 = success, 1 = failure
```

### Common Issues

**"ModuleNotFoundError: No module named 'click'"**
```bash
# Make sure virtual environment is activated
source .venv/bin/activate
pip install -r requirements.txt
```

**"Agent test directory not found"**
```bash
# Check agent name and directory structure
python -m ai_answer_checker --list-agents
ls agent_tests/
```

**"Connection refused" or AI Agent Down**
```bash
# Use dry run mode to test without AI agent
python -m ai_answer_checker --agent pay-details-us-agent --dry-run

# Test against real services (bypassing stubs) - useful for GitPod/cloud environments
python -m ai_answer_checker --agent pay-details-us-agent --no-stubs
```

**"YAML parsing errors" or malformed test files**
- YAML parsing errors are now shown in test reports with detailed error messages
- Check test file syntax with: `python -c "import yaml; yaml.safe_load(open('your_test.yaml'))"`

**"Stub service port conflicts"**
```bash
# If port 9876 is in use, kill the process or skip stubs entirely
lsof -i :9876  # Find what's using the port
kill -9 PID    # Kill the process using the port

# Or skip stubs entirely for integration testing
python -m ai_answer_checker.cli --agent pay-details-us-agent --no-stubs
```

**"HTTP 500 errors" or truncated error messages**
- Full error messages are now displayed without truncation
- HTTP errors (401, 403, 500) are highlighted with 🚨 icons
- Check actual HTTP response bodies in the CSV reports

## 🎯 Exit Codes

The tool returns appropriate exit codes for CI/CD integration:

- **0** - Success (all tests passed and threshold met)
- **1** - Failure (tests failed, errors occurred, or threshold not met)

## 📋 Best Practices

### Test Organization
- Create one test file per scenario
- Use descriptive test names
- Group related tests in subdirectories if needed

### Environment Management
- Use different thresholds for different environments
- Store secrets in environment variables, not config files
- Test against staging before production

### CI/CD Integration
- Start with dry runs in CI
- Use JSON format for automated parsing
- Set appropriate thresholds for your use case
- Archive test reports as build artifacts

### Response Quality
- Use exact matching for deterministic outputs
- Use semantic matching for varied but equivalent responses  
- Use substring matching for keyword validation
- Adjust thresholds based on your quality requirements

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

[Add your license information here]

## 🆘 Support

For issues and questions:
1. Check the debugging section above
2. Review the examples in the `examples/`, `unit_tests/`, and `agent_tests/` directories
3. Open an issue on GitHub
4. Contact the development team

---

**Happy Testing!** 🚀