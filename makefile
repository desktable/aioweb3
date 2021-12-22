all: format lint test
.PHONY: all

format:
	poetry run autoflake --recursive --verbose --remove-all-unused-imports --ignore-init-module-imports --in-place aioweb3
	poetry run isort --py auto aioweb3
	poetry run black aioweb3

	# format the "tests" folder
	poetry run isort --py auto tests
	poetry run black tests
.PHONY: format

lint:
	poetry run mypy aioweb3
	poetry run flake8 aioweb3
	poetry run pylint --fail-under=7.5 aioweb3
.PHONY: lint

test:
	poetry run pytest tests
.PHONY: test

# for github actions
check-format:
	poetry run isort --py auto aioweb3 --check
	poetry run black aioweb3 --check
.PHONY: check-format
