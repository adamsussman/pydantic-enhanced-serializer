#!/usr/bin/env bash

set -e
set -x

isort -c pydantic_sparsefields tests
black --check pydantic_sparsefields tests
flake8 pydantic_sparsefields tests
mypy -p pydantic_sparsefields -p tests
