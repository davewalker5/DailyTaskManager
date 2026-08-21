#!/usr/bin/env bash

set -e

# Activate the virtual environment
export REPORTS_ROOT=$(cd "$(dirname "$0")/.." && pwd)
export PROJECT_ROOT=$(cd "$REPORTS_ROOT/.." && pwd)
export DAILY_TASK_MANAGER_DB=${DAILY_TASK_MANAGER_DB:-"$PROJECT_ROOT/data/taskmanager.db"}
. "$REPORTS_ROOT/venv/bin/activate"

# Suppress warnings about the output file extension
export PYTHONWARNINGS="ignore"

# Define a list of notebooks to skip
declare -a exclusions=(
    "database.ipynb"
    "export.ipynb"
    "pathutils.ipynb"
    "reporting-utils.ipynb"
)

# Get a list of Jupyter Notebooks and iterate over them
files=$(find "$REPORTS_ROOT/notebooks" -name '*.ipynb')
while IFS= read -r file; do
    # Get the notebook file name and extension without the path
    filename=$(basename -- "$file")

    # See if the notebook is in the exclusions list
    found=0
    if [[ " ${exclusions[@]} " =~ " $filename " ]]; then
        found=1
    fi

    # If this notebook isn't in the exclusions list, run it
    if [[ found -eq 0 ]]; then
        echo "$file"
        papermill "$file" /dev/null --cwd "$(dirname "$file")"
    fi
done <<< "$files"
