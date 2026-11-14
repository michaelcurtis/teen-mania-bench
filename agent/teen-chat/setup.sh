#!/bin/bash
# Installs the Anthropic SDK; the task image already has it, so this is usually a no-op.
set -euo pipefail

python3 -m pip install --quiet anthropic==2.8.0
mkdir -p /logs/teen-chat
