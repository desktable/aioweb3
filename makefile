test:
	poetry run black aioweb3
	poetry run isort aioweb3
	poetry run flake8 aioweb3
	poetry run pytest tests

