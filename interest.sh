#!/bin/bash

# Input JSON file
JSON_FILE="users.json"

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo "jq is required for this script. Please install it and try again."
    exit 1
fi

# Check if the JSON file exists
if [[ ! -f "$JSON_FILE" ]]; then
    echo "File $JSON_FILE not found!"
    exit 1
fi

# Read and update the JSON
UPDATED_JSON=$(jq 'map(.balance = (.balance + (.balance * .interest / 100)))' "$JSON_FILE")

# Check for errors during the jq operation
if [[ $? -ne 0 ]]; then
    echo "Error processing JSON file."
    exit 1
fi

# Save the updated JSON back to the file
echo "$UPDATED_JSON" > "$JSON_FILE"

echo "Balances updated successfully in $JSON_FILE."

