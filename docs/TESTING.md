# Testing Documentation - Shadowrun RPG System

## Overview

This document outlines the testing strategy, procedures, and best practices for the Shadowrun RPG system. Our testing approach emphasizes security, reliability, and performance to ensure a production-ready platform.

## Test Categories

### 1. **Unit Tests**
- **Purpose**: Test individual functions and components in isolation
- **Location**: `tests/unit/`
- **Coverage Target**: 80%
- **Key Areas**:
  - Database models
  - Utility functions
  - Command parsers
  - Validation logic

### 2. **Integration Tests**
- **Purpose**: Test interactions between components
- **Location**: `tests/integration/`
- **Coverage Target**: 70%
- **Key Areas**:
  - API endpoints
  - Database operations
  - External service integrations
  - WebSocket communications

### 3. **End-to-End (E2E) Tests**
- **Purpose**: Test complete user workflows
- **Location**: `tests/e2e/`
- **Coverage Target**: Core workflows
- **Key Areas**:
  - Session creation and joining
  - Character creation flow
  - DM review process
  - Image generation workflow
  - Slack command flow

### 4. **Security Tests**
- **Purpose**: Identify vulnerabilities and ensure secure operations
- **Location**: `tests/test_security.py`
- **Key Areas**:
  - Input validation
  - Authentication/authorization
  - Injection attacks
  - XSS/CSRF protection
  - Rate limiting

### 5. **Performance Tests**
- **Purpose**: Ensure system performs under load
- **Location**: `tests/performance/`
- **Key Areas**:
  - Concurrent user handling
  - Database query optimization
  - WebSocket scalability
  - API response times

### 6. **Race Condition Tests**
- **Purpose**: Ensure thread safety and data consistency
- **Location**: `tests/test_race_conditions.py`
- **Key Areas**:
  - Concurrent session joins
  - Simultaneous DM approvals
  - Parallel image generation
  - WebSocket message ordering

## Running Tests

### Quick Start
```bash
# Run all tests
make test

# Run specific test categories
make test-security      # Security tests only
make test-race         # Race condition tests
make test-coverage     # With coverage report
make test-perf        # Performance tests

# Run complete QA suite
make qa
```

### Backend Testing
```bash
# Run all backend tests
cd shadowrun-backend
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=html

# Run specific test file
python -m pytest tests/test_security.py -v

# Run specific test
python -m pytest tests/test_security.py::TestSecurityVulnerabilities::test_xss_in_chat_messages -v
```

### Frontend Testing
```bash
# Run all frontend tests
cd shadowrun-interface
npm test

# Run with coverage
npm run test:coverage

# Run in watch mode
npm run test:watch

# Run specific test file
npm test ShadowrunConsole.test.tsx
```

## Test Structure

### Backend Test Organization
```
shadowrun-backend/
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Shared fixtures
│   ├── test_security.py     # Security tests
│   ├── test_race_conditions.py # Race condition tests
│   ├── unit/
│   │   ├── test_models.py
│   │   ├── test_utils.py
│   │   └── test_validators.py
│   ├── integration/
│   │   ├── test_api.py
│   │   ├── test_websocket.py
│   │   └── test_slack.py
│   └── e2e/
│       ├── test_session_flow.py
│       ├── test_dm_workflow.py
│       └── test_player_journey.py
```

### Frontend Test Organization
```
shadowrun-interface/
├── tests/
│   ├── components/
│   │   ├── ShadowrunConsole.test.tsx
│   │   ├── DmDashboard.test.tsx
│   │   └── ImageGallery.test.tsx
│   ├── integration/
│   │   ├── api.test.ts
│   │   └── websocket.test.ts
│   └── e2e/
│       └── userflows.test.ts
```

## Writing Tests

### Test Naming Convention
```python
# Backend (pytest)
def test_should_reject_xss_in_user_input():
    """Test that XSS attempts are sanitized in user input"""
    pass

# Frontend (Jest)
describe('ShadowrunConsole', () => {
  it('should display error message on network failure', () => {
    // test implementation
  });
});
```

### Backend Test Template
```python
import pytest
from app import app, db

class TestFeatureName:
    @pytest.fixture
    def client(self):
        app.config['TESTING'] = True
        with app.test_client() as client:
            with app.app_context():
                db.create_all()
                yield client
    
    def test_specific_behavior(self, client):
        """Test description"""
        # Arrange
        test_data = {'key': 'value'}
        
        # Act
        response = client.post('/api/endpoint', json=test_data)
        
        # Assert
        assert response.status_code == 200
        assert response.json['success'] == True
```

### Frontend Test Template
```typescript
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ComponentName } from '@/components/ComponentName';

describe('ComponentName', () => {
  it('should handle user interaction correctly', async () => {
    // Arrange
    const user = userEvent.setup();
    render(<ComponentName />);
    
    // Act
    const button = screen.getByRole('button', { name: /submit/i });
    await user.click(button);
    
    // Assert
    await waitFor(() => {
      expect(screen.getByText(/success/i)).toBeInTheDocument();
    });
  });
});
```

## Security Testing Checklist

### Input Validation
- [ ] Command injection (shell commands)
- [ ] SQL injection
- [ ] NoSQL injection
- [ ] XSS (Cross-Site Scripting)
- [ ] XXE (XML External Entity)
- [ ] Path traversal
- [ ] Template injection
- [ ] LDAP injection

### Authentication & Authorization
- [ ] Missing authentication on sensitive endpoints
- [ ] Privilege escalation
- [ ] Session fixation
- [ ] Token leakage
- [ ] Insecure direct object references

### Network Security
- [ ] CSRF protection
- [ ] CORS configuration
- [ ] SSL/TLS implementation
- [ ] Security headers
- [ ] Rate limiting

### Data Protection
- [ ] Sensitive data exposure
- [ ] Insecure cryptographic storage
- [ ] Insufficient transport layer protection
- [ ] Information disclosure

## Performance Testing

### Load Testing Scenarios
1. **Normal Load**: 50 concurrent users
2. **Peak Load**: 200 concurrent users
3. **Stress Test**: 500+ concurrent users
4. **Spike Test**: Sudden increase from 50 to 300 users

### Performance Metrics
- Response time (p50, p95, p99)
- Throughput (requests per second)
- Error rate
- Resource utilization (CPU, memory)
- Database query performance

### Running Performance Tests
```bash
# Using Locust
cd shadowrun-backend
locust -f tests/test_performance.py --headless -u 100 -r 10 -t 60s

# Custom stress test
python tests/test_stress.py
```

## Continuous Integration

### GitHub Actions Workflow
```yaml
name: Test Suite
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: make test
      - name: Security scan
        run: make audit
```

## Test Data Management

### Generating Test Data
```bash
# Generate test data
make test-data

# Reset database with test data
make db-reset
python scripts/seed_test_data.py
```

### Test User Accounts
```
GM Account:
- Username: gm_test
- Password: test123
- Role: Game Master

Player Accounts:
- Username: player1_test
- Password: test123
- Role: Player
```

## Debugging Tests

### Verbose Output
```bash
# Maximum verbosity
pytest -vvv tests/

# Show print statements
pytest -s tests/

# Stop on first failure
pytest -x tests/

# Run last failed tests
pytest --lf tests/
```

### Debug Mode
```python
# Add breakpoint in test
import pdb; pdb.set_trace()

# Or use pytest's built-in
pytest --pdb tests/
```

## Coverage Requirements

### Minimum Coverage Targets
- **Overall**: 70%
- **Critical Paths**: 90%
- **Security Functions**: 95%
- **New Code**: 80%

### Viewing Coverage Reports
```bash
# Generate HTML report
make test-coverage

# View in browser
open shadowrun-backend/htmlcov/index.html
```

## Best Practices

### Do's
- ✅ Write tests before fixing bugs
- ✅ Test edge cases and error conditions
- ✅ Use descriptive test names
- ✅ Keep tests independent
- ✅ Mock external dependencies
- ✅ Test both success and failure paths

### Don'ts
- ❌ Don't test implementation details
- ❌ Don't use production data
- ❌ Don't skip flaky tests (fix them)
- ❌ Don't test third-party libraries
- ❌ Don't write overly complex tests

## Troubleshooting

### Common Issues

**SQLAlchemy DetachedInstanceError**
```python
# Fix: Use app context
with app.app_context():
    # Database operations here
```

**WebSocket Connection Errors**
```python
# Fix: Mock WebSocket in tests
global.WebSocket = MockWebSocket
```

**Async Test Failures**
```python
# Fix: Use pytest-asyncio
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
```

## Future Improvements

1. **Visual Regression Testing**
   - Screenshot comparison for UI changes
   - Automated visual diff reports

2. **Mutation Testing**
   - Ensure test quality with mutation analysis
   - Identify untested code paths

3. **Contract Testing**
   - API contract validation
   - Frontend-backend integration contracts

4. **Chaos Engineering**
   - Random failure injection
   - Network partition simulation
   - Resource exhaustion testing 