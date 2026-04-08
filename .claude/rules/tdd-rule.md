---
alwaysApply: true
---

# TDD Enforcement Rule

## Rule
Write a failing test BEFORE writing any implementation code.

## Process
1. Red: Write a test that fails because the code doesn't exist yet
2. Green: Write the minimum code to make the test pass
3. Refactor: Clean up while keeping tests green

## Enforcement
- Check test-cases.md for the corresponding test case before implementing
- If no test exists for the code you are about to write, write the test first
- Run pytest -v after each step to verify
- Do not move to the next module until all current tests pass

## Location
- Tests: tests/test_{module_name}.py
- Use pytest fixtures, not setUp/tearDown
- Mock all external services (boto3, Bedrock)
- Use tmp_path fixture for filesystem tests
