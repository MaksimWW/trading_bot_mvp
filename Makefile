
.PHONY: format lint check-format install-tools

# Install formatting tools
install-tools:
	pip install black isort flake8

# Format all Python code
format:
	python -m black src/ tests/ --line-length=100
	python -m isort src/ tests/ --profile=black --line-length=100

# Run linting checks
lint:
	python -m flake8 src/ tests/ --max-line-length=100 --max-complexity=10

# Check if code is properly formatted (like CI/CD)
check-format:
	python -m black --check src/ tests/ --line-length=100
	python -m isort --check-only src/ tests/ --profile=black --line-length=100
	python -m flake8 src/ tests/ --max-line-length=100 --max-complexity=10

# Format and commit (safe workflow)
safe-commit:
	make format
	make check-format
	git add .
	@echo "Ready to commit with: git commit -m 'your message'"
