#!/bin/bash
# PM2 v6 wrapper — sets env vars and runs Python scripts
# Usage: cloud-start.sh <script.py> [args...]
export FTE_ROLE=cloud
export VAULT_PATH=/home/ubuntu/AI_Employee_Vault
export PROJECT_ROOT=/home/ubuntu/AI_Employee_Vault
export GIT_SYNC_INTERVAL_SECONDS=60
export DRY_RUN=true

cd /home/ubuntu/AI_Employee_Vault
exec /home/ubuntu/fte-env/bin/python3 "$@"
