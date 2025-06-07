#!/bin/bash

# Shadowrun RPG Development Environment Script
# This script helps manage the development workflow for both backend and frontend

# Set paths (adjust according to your actual monorepo structure)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$ROOT_DIR"
FRONTEND_DIR="$(realpath "$ROOT_DIR/../shadowrun-interface")"

# Function to display help
show_help() {
    echo "Shadowrun RPG Development Helper"
    echo ""
    echo "Usage: ./dev.sh [command]"
    echo ""
    echo "Commands:"
    echo "  start         Start both backend and frontend development servers"
    echo "  start:back    Start only the backend server"
    echo "  start:front   Start only the frontend server"
    echo "  test          Run all tests (backend and frontend)"
    echo "  test:back     Run backend tests"
    echo "  test:front    Run frontend tests"
    echo "  db:reset      Reset the database to initial state"
    echo "  db:seed       Seed the database with sample data"
    echo "  setup         Install all dependencies (both backend and frontend)"
    echo "  lint          Run linters on all code"
    echo "  clean         Clean temporary files and caches"
    echo "  help          Show this help message"
}

# Check if required tools are installed
check_requirements() {
    local requirements_met=true
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python 3 is not installed"
        requirements_met=false
    fi
    
    # Check npm/node
    if ! command -v npm &> /dev/null; then
        echo "❌ npm is not installed"
        requirements_met=false
    fi
    
    if [ "$requirements_met" = false ]; then
        echo "Please install the required tools before running this script."
        exit 1
    fi
    
    return 0
}

# Function to start the backend server
start_backend() {
    echo "🔧 Starting Shadowrun backend server..."
    cd "$BACKEND_DIR" || exit 1
    python app.py
}

# Function to start the frontend server
start_frontend() {
    echo "🔧 Starting Shadowrun frontend server..."
    cd "$FRONTEND_DIR" || exit 1
    npm run dev
}

# Function to start both servers (in separate terminals)
start_both() {
    echo "🚀 Starting complete Shadowrun development environment..."
    # Using gnome-terminal, adjust for your preferred terminal
    gnome-terminal --tab --title="Backend" --command="bash -c 'cd \"$BACKEND_DIR\" && python app.py; bash'" \
                  --tab --title="Frontend" --command="bash -c 'cd \"$FRONTEND_DIR\" && npm run dev; bash'"
    
    echo "✅ Development servers started in new terminal tabs"
}

# Reset the database
reset_database() {
    echo "🔄 Resetting database..."
    cd "$BACKEND_DIR" || exit 1
    # Adjust according to your actual reset mechanism
    rm -f shadowrun.db
    python -c "from app import db; db.create_all()"
    echo "✅ Database reset complete"
}

# Seed the database with test data
seed_database() {
    echo "🌱 Seeding database with sample data..."
    cd "$BACKEND_DIR" || exit 1
    python scripts/seed_data.py
    echo "✅ Database seeded successfully"
}

# Run backend tests
run_backend_tests() {
    echo "🧪 Running backend tests..."
    cd "$BACKEND_DIR" || exit 1
    pytest
}

# Run frontend tests
run_frontend_tests() {
    echo "🧪 Running frontend tests..."
    cd "$FRONTEND_DIR" || exit 1
    npm test
}

# Run all tests
run_all_tests() {
    run_backend_tests
    run_frontend_tests
}

# Setup development environment
setup_environment() {
    echo "🔧 Setting up development environment..."
    
    # Backend setup
    echo "Setting up backend..."
    cd "$BACKEND_DIR" || exit 1
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    
    # Frontend setup
    echo "Setting up frontend..."
    cd "$FRONTEND_DIR" || exit 1
    npm install
    
    echo "✅ Development environment setup complete"
}

# Run linters
run_linters() {
    echo "🔍 Running linters..."
    
    # Backend linting
    echo "Linting backend code..."
    cd "$BACKEND_DIR" || exit 1
    flake8
    
    # Frontend linting
    echo "Linting frontend code..."
    cd "$FRONTEND_DIR" || exit 1
    npm run lint
    
    echo "✅ Linting complete"
}

# Clean temporary files
clean_environment() {
    echo "🧹 Cleaning environment..."
    
    # Backend cleaning
    cd "$BACKEND_DIR" || exit 1
    find . -type d -name "__pycache__" -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete
    
    # Frontend cleaning
    cd "$FRONTEND_DIR" || exit 1
    rm -rf node_modules/.cache
    
    echo "✅ Cleaning complete"
}

# Check requirements first
check_requirements

# Process command line arguments
if [ $# -eq 0 ]; then
    show_help
    exit 0
fi

case "$1" in
    start)
        start_both
        ;;
    start:back)
        start_backend
        ;;
    start:front)
        start_frontend
        ;;
    test)
        run_all_tests
        ;;
    test:back)
        run_backend_tests
        ;;
    test:front)
        run_frontend_tests
        ;;
    db:reset)
        reset_database
        ;;
    db:seed)
        seed_database
        ;;
    setup)
        setup_environment
        ;;
    lint)
        run_linters
        ;;
    clean)
        clean_environment
        ;;
    help|*)
        show_help
        ;;
esac

exit 0