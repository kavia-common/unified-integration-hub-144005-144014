#!/bin/bash
cd /home/kavia/workspace/code-generation/unified-integration-hub-144005-144014/unified_connector_backend
source venv/bin/activate
flake8 .
LINT_EXIT_CODE=$?
if [ $LINT_EXIT_CODE -ne 0 ]; then
  exit 1
fi

