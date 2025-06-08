#!/bin/bash
# Development setup script for Shadowrun RPG System

set -e  # Exit on error

echo "=================================================="
echo "Shadowrun RPG System - Development Setup"
echo "=================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Check prerequisites
echo "Checking prerequisites..."

# Check Python
if command -v python3 &> /dev/null; then
    print_status "Python 3 found: $(python3 --version)"
else
    print_error "Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi

# Check Node.js
if command -v node &> /dev/null; then
    print_status "Node.js found: $(node --version)"
else
    print_error "Node.js not found. Please install Node.js 14 or higher."
    exit 1
fi

# Check npm
if command -v npm &> /dev/null; then
    print_status "npm found: $(npm --version)"
else
    print_error "npm not found. Please install npm."
    exit 1
fi

# Check Docker (optional)
if command -v docker &> /dev/null; then
    print_status "Docker found: $(docker --version)"
else
    print_warning "Docker not found. Docker is optional but recommended for testing."
fi

# Check PostgreSQL/SQLite
if command -v sqlite3 &> /dev/null; then
    print_status "SQLite3 found"
else
    print_warning "SQLite3 not found. Will use SQLite from Python."
fi

echo ""
echo "Setting up backend..."
echo "--------------------"

# Navigate to backend directory
cd "$(dirname "$0")/.."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    print_status "Creating Python virtual environment..."
    python3 -m venv venv
else
    print_status "Virtual environment already exists"
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip

# Install backend dependencies
print_status "Installing backend dependencies..."
pip install -r requirements.txt

# Install development dependencies
if [ -f "requirements-dev.txt" ]; then
    print_status "Installing development dependencies..."
    pip install -r requirements-dev.txt
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    print_status "Creating .env file..."
    cat > .env << EOL
# Shadowrun Backend Configuration
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=dev-secret-key-change-in-production
DATABASE_URL=sqlite:///shadowrun.db

# API Keys (Add your own)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GROQ_API_KEY=
SLACK_BOT_TOKEN=
SLACK_SIGNING_SECRET=
SLACK_APP_TOKEN=

# Image Generation
DALLE_API_KEY=
STABLE_DIFFUSION_API_KEY=

# Redis (optional)
REDIS_HOST=localhost
REDIS_PORT=6379

# JWT Configuration
JWT_SECRET=shadowrun-secret-key-change-in-production
JWT_EXPIRATION=3600
EOL
    print_warning "Created .env file. Please add your API keys!"
else
    print_status ".env file already exists"
fi

# Initialize database
print_status "Initializing database..."
python3 -c "from app import app, db; app.app_context().push(); db.create_all(); print('Database initialized')"

# Create test data directory
if [ ! -d "tests/data" ]; then
    print_status "Creating test data directory..."
    mkdir -p tests/data
fi

# Install pre-commit hooks
if command -v pre-commit &> /dev/null; then
    print_status "Installing pre-commit hooks..."
    pre-commit install
else
    print_warning "pre-commit not found. Run 'pip install pre-commit' to enable hooks."
fi

echo ""
echo "Setting up frontend..."
echo "---------------------"

# Navigate to frontend directory
cd ../shadowrun-interface

# Install frontend dependencies
print_status "Installing frontend dependencies..."
npm install

# Create .env.local file if it doesn't exist
if [ ! -f ".env.local" ]; then
    print_status "Creating .env.local file..."
    cat > .env.local << EOL
# Shadowrun Frontend Configuration
NEXT_PUBLIC_API_URL=http://localhost:5000
NEXT_PUBLIC_WS_URL=ws://localhost:5000

# Clerk Authentication (Add your keys)
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=
CLERK_SECRET_KEY=

# Optional Features
NEXT_PUBLIC_ENABLE_IMAGE_GENERATION=true
NEXT_PUBLIC_ENABLE_SLACK_INTEGRATION=true
EOL
    print_warning "Created .env.local file. Please add your Clerk API keys!"
else
    print_status ".env.local file already exists"
fi

# Build frontend
print_status "Building frontend assets..."
npm run build

echo ""
echo "Creating useful scripts..."
echo "-------------------------"

# Create run script
cat > ../run-dev.sh << 'EOL'
#!/bin/bash
# Start both backend and frontend in development mode

echo "Starting Shadowrun development servers..."
echo "Backend: http://localhost:5000"
echo "Frontend: http://localhost:3000"
echo "Press Ctrl+C to stop"

# Function to cleanup on exit
cleanup() {
    echo -e "\nStopping servers..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit
}

trap cleanup INT TERM

# Start backend
cd shadowrun-backend
source venv/bin/activate
python app.py &
BACKEND_PID=$!

# Start frontend
cd ../shadowrun-interface
npm run dev &
FRONTEND_PID=$!

# Wait for both processes
wait
EOL

chmod +x ../run-dev.sh
print_status "Created run-dev.sh script"

# Create test script
cat > ../run-tests.sh << 'EOL'
#!/bin/bash
# Run all tests with coverage

echo "Running Shadowrun test suite..."

# Backend tests
echo -e "\n=== Backend Tests ==="
cd shadowrun-backend
source venv/bin/activate
python -m pytest tests/ -v --cov=. --cov-report=html --cov-report=term

# Frontend tests
echo -e "\n=== Frontend Tests ==="
cd ../shadowrun-interface
npm test -- --coverage

echo -e "\nTest run complete!"
echo "Backend coverage report: shadowrun-backend/htmlcov/index.html"
echo "Frontend coverage report: shadowrun-interface/coverage/lcov-report/index.html"
EOL

chmod +x ../run-tests.sh
print_status "Created run-tests.sh script"

echo ""
echo "Creating test fixtures..."
echo "------------------------"

# Create test fixtures
cd ../shadowrun-backend
python3 << 'EOF'
import json
import os

# Create test fixtures directory
os.makedirs('tests/fixtures', exist_ok=True)

# Sample character fixture
character_fixture = {
    "name": "Test Runner",
    "handle": "Shadow",
    "archetype": "Street Samurai",
    "attributes": {
        "body": 4,
        "agility": 5,
        "reaction": 4,
        "strength": 3,
        "willpower": 3,
        "logic": 3,
        "intuition": 4,
        "charisma": 2,
        "edge": 3
    },
    "skills": {
        "firearms": 6,
        "close_combat": 4,
        "stealth": 5,
        "perception": 4
    }
}

# Sample session fixture
session_fixture = {
    "name": "Test Campaign",
    "gm_user_id": "test_gm_user",
    "players": [
        {"user_id": "player1", "character_name": "Shadow"},
        {"user_id": "player2", "character_name": "Decker"}
    ]
}

# Save fixtures
with open('tests/fixtures/character.json', 'w') as f:
    json.dump(character_fixture, f, indent=2)

with open('tests/fixtures/session.json', 'w') as f:
    json.dump(session_fixture, f, indent=2)

print("Test fixtures created")
EOF

print_status "Created test fixtures"

echo ""
echo "Generating documentation..."
echo "--------------------------"

# Create docs directory
mkdir -p ../docs

# Create TESTING.md
cat > ../docs/TESTING.md << 'EOL'
# Shadowrun RPG System - Testing Guide

## Test Categories

### Unit Tests
- **Backend**: `tests/test_*.py`
- **Frontend**: `tests/components/*.test.tsx`
- Coverage target: 80%+

### Integration Tests
- **API Tests**: `tests/test_api_integration.py`
- **WebSocket Tests**: `tests/ws/reconnection.test.ts`
- **Slack Integration**: `tests/test_slack_integration.py`

### Security Tests
- **Input Validation**: `tests/test_security.py`
- **AI Input Sanitization**: `tests/test_ai_integration.py`
- **XSS Prevention**: Frontend component tests

### Performance Tests
- **Race Conditions**: `tests/test_race_conditions.py`
- **Concurrent Operations**: `tests/test_combat_race.py`
- **Load Testing**: Use `locust` (see Makefile)

## Running Tests

### Quick Test
```bash
make test
```

### Full QA Suite
```bash
make qa
```

### Specific Test Categories
```bash
make test-security    # Security tests only
make test-race       # Race condition tests
make test-coverage   # With coverage report
```

### Frontend Tests
```bash
cd shadowrun-interface
npm test             # Run all tests
npm test -- --watch  # Watch mode
npm test -- --coverage  # With coverage
```

## Writing Tests

### Backend Test Example
```python
def test_dice_roller_edge_case():
    """Test edge case in dice roller"""
    from utils.dice_roller import roll_shadowrun
    
    result = roll_shadowrun(10, edge_used=True)
    assert result['edge_used'] is True
    assert len(result['rolls']) >= 10
```

### Frontend Test Example
```typescript
it('should handle XSS in user input', async () => {
  const user = userEvent.setup();
  render(<DiceRoller />);
  
  const input = screen.getByRole('textbox');
  await user.type(input, '<script>alert("xss")</script>');
  
  expect(screen.queryByText('<script>')).not.toBeInTheDocument();
});
```

## Mocking Guidelines

### Backend Mocks
- LLM calls: Mock `call_llm` in `llm_utils`
- Slack API: Mock `slack_bot.send_message`
- External APIs: Use `responses` or `httpx_mock`

### Frontend Mocks
- API calls: Mock `fetch` globally
- WebSocket: Use `jest-websocket-mock`
- Clerk auth: Mock `@clerk/nextjs`

## CI/CD Integration

Tests run automatically on:
- Pull requests
- Main branch commits
- Pre-deployment checks

## Debugging Failed Tests

1. Run with verbose output: `pytest -vv`
2. Use debugger: `pytest --pdb`
3. Check logs: `tail -f test.log`
4. Inspect fixtures: `pytest --fixtures`
EOL

print_status "Created testing documentation"

echo ""
echo "=================================================="
echo "Development setup complete!"
echo "=================================================="
echo ""
echo "Next steps:"
echo "1. Add your API keys to:"
echo "   - shadowrun-backend/.env"
echo "   - shadowrun-interface/.env.local"
echo ""
echo "2. Run the development servers:"
echo "   ./run-dev.sh"
echo ""
echo "3. Run tests:"
echo "   ./run-tests.sh"
echo ""
echo "4. Access the application:"
echo "   - Frontend: http://localhost:3000"
echo "   - Backend API: http://localhost:5000"
echo ""
echo "Happy coding! 🎮🎲" 