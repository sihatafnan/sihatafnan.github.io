#!/bin/bash

# Check if a commit message was provided
if [ $# -eq 0 ]; then
    echo "No commit message provided. Usage: ./git_push.sh \"Your commit message\""
    exit 1
fi

# Assign the first argument as the commit message
commit_message="$1"

# Staging all changes
git add .

# Committing changes
git commit -m "$commit_message"

# Pushing to GitHub
git push $remote $branch

echo "Changes have been pushed\n"
