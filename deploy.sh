#!/bin/bash

# Set error handling
set -e

# Log file setup
LOG_DIR="$HOME/repos/notes/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/deploy-$(date +%Y%m%d-%H%M%S).log"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to generate commit message based on git status
generate_commit_message() {
    local message=""
    local stats=$(git status --porcelain)
    
    # Count modified, added, and deleted files
    local modified=$(echo "$stats" | grep '^ M\|^MM' | wc -l)
    local added=$(echo "$stats" | grep '^??' | wc -l)
    local deleted=$(echo "$stats" | grep '^ D' | wc -l)
    
    message="Auto-commit: "
    
    if [ $modified -gt 0 ]; then
        message+="$modified files modified"
    fi
    
    if [ $added -gt 0 ]; then
        if [ $modified -gt 0 ]; then
            message+=", "
        fi
        message+="$added files added"
    fi
    
    if [ $deleted -gt 0 ]; then
        if [ $modified -gt 0 ] || [ $added -gt 0 ]; then
            message+=", "
        fi
        message+="$deleted files deleted"
    fi
    
    echo "$message"
}

# Change to the repository directory
cd "$HOME/repos/notes" || {
    log_message "ERROR: Could not change to repository directory"
    exit 1
}

# Activate virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate || {
            log_message "ERROR: Failed to activate virtual environment"
            exit 1
        }
        log_message "Virtual environment activated"
    else
        log_message "ERROR: Virtual environment not found"
        exit 1
    fi
fi

# Check if git repository exists
if [ ! -d .git ]; then
    log_message "ERROR: Not a git repository"
    exit 1
fi

# Execute deployment steps
log_message "Starting deployment process"

# Run clean script
if ! python scripts/clean.py; then
    log_message "ERROR: Clean script failed"
    exit 1
fi
log_message "Clean script completed successfully"

# Run build script
if ! python scripts/build.py . site; then
    log_message "ERROR: Build script failed"
    exit 1
fi
log_message "Build script completed successfully"

# Check if there are any changes to commit
if [ -z "$(git status --porcelain)" ]; then
    log_message "No changes to commit"
    exit 0
fi

# Add all changes
if ! git add .; then
    log_message "ERROR: Failed to stage changes"
    exit 1
fi

# Generate commit message and commit
commit_message=$(generate_commit_message)
if ! git commit -m "$commit_message"; then
    log_message "ERROR: Failed to commit changes"
    exit 1
fi
log_message "Committed changes with message: $commit_message"

# Push changes
if ! git push; then
    log_message "ERROR: Failed to push changes"
    exit 1
fi
log_message "Successfully pushed changes"

log_message "Deployment completed successfully"