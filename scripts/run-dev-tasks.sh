#!/usr/bin/env bash

export PROJECT_ROOT=$( cd "$(dirname "$0")/.." ; pwd -P )
cd "$PROJECT_ROOT"

. venv/bin/activate

unset DAILY_TASK_MANAGER_DB

streamlit run src/streamlit_app.py
