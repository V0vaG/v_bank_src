#!/bin/bash

# Input JSON file
JSON_FILE="/home/$USER/script_files/v_bank/data/users.json"

# Function to check and install dependencies
install_dependencies() {
    local packages=("jq")
    for pkg in "${packages[@]}"; do
        if ! dpkg -l | grep -q "^ii.*$pkg"; then
            echo "Installing $pkg..."
            sudo apt-get update && sudo apt-get install -y "$pkg"
            if [[ $? -ne 0 ]]; then
                echo "Failed to install $pkg. Please check your package manager settings."
                exit 1
            fi
        fi
    done
}

# Ensure dependencies are installed
install_dependencies

# Check if the JSON file exists
if [[ ! -f "$JSON_FILE" ]]; then
    echo "File $JSON_FILE not found!"
    exit 1
fi

# Read and update the JSON
UPDATED_JSON=$(jq 'map(.balance = ((.balance + (.balance * .interest / 100)) * 10 | round) / 10)' "$JSON_FILE")

# Check for errors during the jq operation
if [[ $? -ne 0 ]]; then
    echo "Error processing JSON file."
    exit 1
fi

# Save the updated JSON back to the file
echo "$UPDATED_JSON" > "$JSON_FILE"

echo "Balances updated successfully in $JSON_FILE."
