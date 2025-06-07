# Contributing to Shadowrun RPG System

Thank you for your interest in contributing to the Shadowrun RPG System project! This guide will help you get started as a contributor and provide the necessary information to make your contributions effective and aligned with the project's goals.

## Table of Contents
- [Getting Started](#getting-started)
- [Development Environment](#development-environment)
- [Coding Standards](#coding-standards)
- [Git Workflow](#git-workflow)
- [Pull Request Process](#pull-request-process)
- [Testing Requirements](#testing-requirements)
- [Documentation](#documentation)
- [Community Guidelines](#community-guidelines)

## Getting Started

### Prerequisites
- Python 3.8+
- Node.js 16+
- npm 8+
- Git

### Setting Up Your Environment
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/shadowrun.git
   cd shadowrun
   ```

2. Run the setup script to install both backend and frontend dependencies:
   ```bash
   cd backend
   ./scripts/dev.sh setup
   ```

3. Create a local .env file for environment variables:
   ```bash
   cp backend/.env.example backend/.env
   # Edit .env with your values
   ```

## Development Environment

The project includes a helper script to streamline development tasks:

```bash
./backend/scripts/dev.sh help
```

Common commands:
- `dev.sh start` - Start both backend and frontend servers
- `dev.sh test` - Run all tests
- `dev.sh db:reset` - Reset the database
- `dev.sh db:seed` - Populate the database with sample data

## Coding Standards

### Backend (Python)
- Follow PEP 8 coding style
- Use type hints where possible
- Document functions and classes with docstrings
- Keep functions focused and small

### Frontend (TypeScript/React)
- Follow the project's ESLint and Prettier configurations
- Use functional components and hooks
- Use TypeScript types/interfaces for props and state
- Follow the component organization pattern established in the project

### General
- Write self-documenting code with clear variable and function names
- Keep files focused on a single responsibility
- Add comments for complex logic or business rules
- Include appropriate error handling

## Git Workflow

1. **Branch Naming**:
   - Feature branches: `feature/short-description`
   - Bug fixes: `fix/issue-description`
   - Documentation: `docs/what-is-changing`
   - Example: `feature/dm-review-queue`

2. **Commit Messages**:
   - Begin with a verb in imperative mood
   - Keep the first line under 72 characters
   - Reference issue numbers when applicable
   - Example: `Add DM review queue endpoint (#42)`

3. **Branch Strategy**:
   - Create branches from `main`
   - Keep branches focused on a single feature or fix
   - Rebase your branch before submitting a PR
   - Delete branches after they're merged

## Pull Request Process

1. Create a new branch for your changes
2. Make your changes with appropriate tests and documentation
3. Ensure all tests pass locally
4. Push your branch and create a Pull Request
5. Fill out the PR template with details about your changes
6. Request a review from appropriate team members
7. Address any feedback from reviewers
8. Once approved, your PR will be merged into the main branch

## Testing Requirements

All code contributions should include appropriate tests:

### Backend Tests
- Unit tests for all new functions and classes
- Integration tests for API endpoints
- Test coverage should be maintained or improved

### Frontend Tests
- Component tests for UI components
- Integration tests for complex workflows
- End-to-end tests for critical paths

To run tests:
```bash
# Backend tests
./scripts/dev.sh test:back

# Frontend tests
./scripts/dev.sh test:front
```

## Documentation

Good documentation is essential to the project:

- Update or add API documentation when changing or adding endpoints
- Add JSDoc comments to TypeScript/JavaScript functions and components
- Update the README.md file when making significant changes
- Document complex business logic or architectural decisions

## Community Guidelines

- Be respectful and inclusive in your communication
- Provide constructive feedback on PRs and issues
- Help others when they have questions
- Report bugs or issues with detailed reproduction steps

---

Thank you for contributing to the Shadowrun RPG System project! Your efforts help create an immersive and enjoyable gaming experience for Shadowrun players everywhere.
