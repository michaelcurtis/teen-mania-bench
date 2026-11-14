#!/bin/bash
# Installs the model SDKs; the task image already has them, so this is usually a no-op.
set -euo pipefail

python3 -m pip install --quiet anthropic==2.8.0 openai==3.51.0
mkdir -p /logs/teen-chat
