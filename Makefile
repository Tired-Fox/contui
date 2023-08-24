PROJECT = contui

init:
	pip3 install -e .[tests,dev]
install:
	pip3 install -e .

all:
	make install format lint

format:
	ruff check --fix-only && black $(PROJECT)

lint:
	ruff check ./$(PROJECT)

statistics:
	ruff check --statistics ./$(PROJECT)

type:
	mypy $(PROJECT)

# Testing

test:
	pytest --cov="./$(PROJECT)" tests/

cover:
	coverage html

open:
	python cover.py

test-cov:
	make test cover

# Built/Deploy

build_docs:
	pdoc $(PROJECT) -d google -o docs/

badges:
	python scripts/make_badges.py contui contui

build:
	make badges
	python -m build

deploy:
	python -m twine upload --repository pypi dist/*

build_deploy:
	make build deploy
