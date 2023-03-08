#!/usr/bin/env bash

set -e
set -x

isort pydantic_enhanced_serializer tests
black pydantic_enhanced_serializer tests
flake8 pydantic_enhanced_serializer tests
mypy -p pydantic_enhanced_serializer -p tests
