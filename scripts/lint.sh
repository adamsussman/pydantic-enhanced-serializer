#!/usr/bin/env bash

set -e
set -x

isort -c pydantic_enhanced_serializer tests
black --check pydantic_enhanced_serializer tests
flake8 pydantic_enhanced_serializer tests
mypy -p pydantic_enhanced_serializer -p tests
