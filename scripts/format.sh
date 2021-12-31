#!/usr/bin/env bash

set -e
set -x

isort pydantic_sparsefields tests
black pydantic_sparsefields tests
flake8 pydantic_sparsefields tests
mypy -p pydantic_sparsefields -p tests
