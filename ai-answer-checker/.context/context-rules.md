# AI Context Rules for Python Projects

## Core Rules
1. All AI work must be traceable in Markdown.
2. Tasks must follow the defined lifecycle: `planned → active → completed`.
3. Every session must:
   - Log its date and time
   - Reference the task(s) worked on
   - List files edited
   - Summarize work done and suggest next steps
   - Record the session's purpose (implementation, design, HLD, etc.)
4. Decisions should be recorded with context and rationale.
5. Memory files should reflect shared knowledge, not per-task notes.
6. Use Markdown headings consistently (`#`, `##`, `-`) for structured parsing.

## Python-Specific Guidelines

### Code Standards
1. Follow PEP 8 style guide
2. Use type hints where appropriate
3. Include docstrings for modules, classes, and functions
4. Use meaningful variable and function names
5. Keep functions small and focused (SOLID principles)

### Package Management
1. Use `pyproject.toml` for project configuration
2. Manage dependencies through `requirements.txt` or `pyproject.toml`
3. Use virtual environments for isolation
4. Pin dependency versions for reproducibility

### Testing Standards
1. Use pytest for testing framework
2. Maintain test coverage above 80%
3. Write unit tests for core functionality
4. Include integration tests for external dependencies
5. Use mocking for external services

### File Structure
1. Follow Python package conventions:
   - `__init__.py` files for packages
   - `__main__.py` for CLI entry points
   - Separate modules by responsibility
2. Use snake_case for files and variables
3. Use PascalCase for classes
4. Group related functionality in modules

## Session Management

### Session Purpose
- Every session must begin with identifying its purpose
- Common purposes include: implementation, design, debugging, refactoring, testing
- Purpose must be documented in the session log
- Purpose guides the level of detail and approach

### Code Generation Guidelines
- Ask clarifying questions before writing code
- Understand requirements thoroughly before implementation
- Generate code once and well, avoiding multiple iterations
- Document design decisions and trade-offs
- Consider edge cases and error handling upfront
- Include proper exception handling
- Add logging where appropriate

### Change Logging
- All changes to `.context` directory must be logged
- Logs must include:
  - Timestamp
  - Changed files
  - Purpose of changes
  - Impact assessment
  - Related tasks or issues
- Logs should be stored in `.context/sessions/` with appropriate naming

## Project Context Structure

### Required Directory Structure
```
.context/
├── documents/          # Project documentation
├── plans/             # Implementation plans
├── sessions/          # Session logs
├── tasks/             # Task definitions
└── templates/         # Reusable templates
```

### Essential Files
- `context-rules.md`: Project rules and patterns
- `plans/plan1.md`: Implementation plan
- `plans/tasks-list.md`: Task breakdown

## Implementation Guidelines

### Task Creation
- Small and focused
- Clear objectives
- Dependencies listed
- Acceptance criteria
- Implementation notes
- Consider Python-specific requirements (virtual env, dependencies, etc.)

### Plan Creation
- Phased approach
- Technical considerations
- Required changes
- Success criteria
- Performance impact
- Python package structure considerations

## Python Best Practices

### Code Quality
1. Use linting tools (flake8, pylint, black)
2. Type checking with mypy
3. Security scanning with bandit
4. Dependency vulnerability scanning

### Performance
1. Profile before optimizing
2. Use appropriate data structures
3. Consider memory usage
4. Implement caching where beneficial

### Error Handling
1. Use specific exception types
2. Include meaningful error messages
3. Log errors appropriately
4. Handle edge cases gracefully

### Documentation
1. Clear and concise docstrings
2. Include examples in documentation
3. Keep README.md updated
4. Document API endpoints for web services

## Review Checklist
- [ ] Required directories created
- [ ] Essential files in place
- [ ] Documentation complete
- [ ] Tasks properly defined
- [ ] Plans comprehensive
- [ ] References accurate
- [ ] Python best practices included
- [ ] Type hints added where appropriate
- [ ] Tests included
- [ ] Dependencies properly managed
- [ ] Error handling implemented
- [ ] Logging configured

## PR Guidelines for Python

### PR Creation
- Keep PRs small and focused (200-400 lines of code)
- Include appropriate tests
- Update documentation
- Follow existing code patterns
- Include type hints
- Add or update docstrings
- Ensure linting passes

### Python-Specific PR Checklist
- [ ] Code follows PEP 8
- [ ] Type hints added
- [ ] Docstrings updated
- [ ] Tests added/updated
- [ ] Dependencies updated if needed
- [ ] Virtual environment tested
- [ ] No security vulnerabilities
- [ ] Performance impact considered
- [ ] Error handling appropriate
- [ ] Logging configured properly