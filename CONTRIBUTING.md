# Contributing to Audio Transcription Service

Thank you for your interest in contributing! This document provides guidelines for contributing to this project.

## Getting Started

1. **Fork the repository** and clone it locally
2. **Set up the development environment**:
   ```bash
   cp .env.example .env
   docker-compose up --build
   ```
3. **Create a branch** for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Guidelines

### Code Style

- **Python**: Follow PEP 8 guidelines
- **JavaScript**: Use ES6+ features, maintain consistent formatting
- **Comments**: Write clear, concise comments for complex logic
- **Naming**: Use descriptive variable and function names

### Testing

Before submitting a pull request:

1. Test your changes locally
2. Ensure all existing functionality still works
3. Add tests for new features when applicable
4. Run the test suite:
   ```bash
   docker-compose run --rm transcription-service pytest tests/
   ```

### Commit Messages

Write clear, descriptive commit messages:

- Use present tense ("Add feature" not "Added feature")
- Keep the first line under 50 characters
- Provide detailed description in the body if needed

Example:
```
Add speaker diarization caching

- Implement LRU cache with 24h TTL
- Add cache statistics endpoint
- Update documentation
```

## Pull Request Process

1. **Update documentation** if you're changing functionality
2. **Update CHANGELOG.md** with your changes
3. **Ensure your code builds** without errors
4. **Submit the pull request** with a clear description of changes
5. **Respond to feedback** from reviewers

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How has this been tested?

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Tests added/updated
- [ ] CHANGELOG.md updated
```

## Reporting Bugs

When reporting bugs, please include:

1. **Description**: Clear description of the issue
2. **Steps to Reproduce**: Detailed steps to reproduce the behavior
3. **Expected Behavior**: What you expected to happen
4. **Actual Behavior**: What actually happened
5. **Environment**: 
   - OS version
   - Docker version
   - Browser (if frontend issue)
6. **Logs**: Relevant error messages or logs
7. **Screenshots**: If applicable

## Feature Requests

We welcome feature requests! Please:

1. **Search existing issues** to avoid duplicates
2. **Describe the feature** clearly
3. **Explain the use case** and benefits
4. **Provide examples** if possible

## Code Review Process

All submissions require review. We aim to:

- Review pull requests within 3-5 business days
- Provide constructive feedback
- Merge approved changes promptly

## Development Setup

### Prerequisites

- Docker & Docker Compose
- Git
- (Optional) Python 3.11+ for local development
- (Optional) NVIDIA GPU with CUDA for GPU acceleration

### Local Development Without Docker

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env

# Run migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload
```

### Project Structure

```
.
├── app/                    # Application code
│   ├── api/               # API routes
│   ├── core/              # Core configuration
│   ├── models/            # Database models
│   ├── services/          # Business logic
│   └── utils/             # Utility functions
├── static/                # Frontend assets
├── templates/             # HTML templates
├── scripts/               # Utility scripts
├── tests/                 # Test suite
└── docker-compose.yml     # Docker configuration
```

## Questions?

Feel free to open an issue for questions or discussions.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
