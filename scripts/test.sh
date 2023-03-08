#!/usr/bin/env bash

set -e
set -x

pytest --doctest-modules --ignore-glob="pydantic_enhanced_serializer/integrations/*" . $@
