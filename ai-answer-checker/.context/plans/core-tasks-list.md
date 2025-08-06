# Core Tasks List - AI Answer Checker

## Implementation Priority (Based on HLD Document)

### TASK-001: YAML Configuration Loading
**Status**: Planned  
**Priority**: Critical  
**Dependencies**: None

**Description**: Implement YAML configuration loading functionality that allows the CLI to read test configurations based on agent parameter.

**Key Deliverables**:
- CLI accepts `--agent <name>` parameter
- Loads configuration from `configs/<name>.yaml`
- Validates configuration structure with Pydantic
- Handles missing or malformed config files

**Files**: `models.py`, `runner.py`, `cli.py`, `configs/demo.yaml`

### TASK-002: Basic HTTP Client
**Status**: Planned  
**Priority**: Critical  
**Dependencies**: TASK-001

**Description**: Implement HTTP client functionality to communicate with AI agent endpoints based on configuration.

**Key Deliverables**:
- Send requests to AI agent endpoints
- Support authentication and custom headers
- Implement timeout and retry logic
- Handle different request/response formats

**Files**: `http_client.py`, `models.py`, `runner.py`

### TASK-003: Response Comparison
**Status**: Planned  
**Priority**: Critical  
**Dependencies**: TASK-002

**Description**: Implement response comparison logic to validate AI agent responses against expected results.

**Key Deliverables**:
- Support exact match, substring, regex comparison
- Handle JSON and text response formats
- Generate detailed diff reports
- Return clear pass/fail determinations

**Files**: `comparison.py`, `models.py`, `runner.py`

### TASK-004: Test Execution & Reporting
**Status**: Planned  
**Priority**: Critical  
**Dependencies**: TASK-001, TASK-002, TASK-003

**Description**: Implement test orchestration and reporting functionality to execute test suites and generate comprehensive reports.

**Key Deliverables**:
- Execute test suites from configuration
- Real-time progress reporting
- Generate console and file reports
- Return appropriate exit codes for CI/CD

**Files**: `runner.py`, `reporting.py`, `cli.py`

## Task Implementation Order
1. **TASK-001** (Config loading) - Foundation
2. **TASK-002** (HTTP client) - Communication
3. **TASK-003** (Comparison) - Validation
4. **TASK-004** (Orchestration) - Complete flow

## Success Definition
- CLI tool that reads YAML configs
- Executes HTTP requests to AI agents
- Compares responses and reports results
- Generates usable test reports for CI/CD