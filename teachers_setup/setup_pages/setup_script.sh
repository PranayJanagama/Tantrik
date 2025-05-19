#!/bin/bash

# 1. Generate SSH keys (only if they don't exist)
echo "Checking SSH keys..."

if [ ! -f /root/.ssh/id_rsa ]; then
    echo "Generating SSH key..."
    mkdir -p /root/.ssh
    ssh-keygen -t rsa -b 4096 -f /root/.ssh/id_rsa -N ""
    chmod 700 /root/.ssh
    chmod 600 /root/.ssh/id_rsa
    chmod 644 /root/.ssh/id_rsa.pub
    echo "SSH keys generated."
else
    echo "SSH keys already exist. Skipping generation."
fi

# Iterate over each directory in /home
for dir in /home/*; do
    if [ -d "$dir" ]; then
        username=$(basename "$dir")

        # Check if the user already exists
        if id "$username" &>/dev/null; then
            echo "User $username already exists."
        else
            # Create the user with specific UID and GID
            useradd -d "$dir" "$username"
            echo "Created user $username."
        fi

        # Ensure the user owns their home directory
        chown -R "$username:$username" "$dir"
        chmod -R 755 "$dir"
        export PATH="$dir/.local/bin:$PATH"
    fi
done

echo "Setting up Python virtual environment..."

cd /home/tele/Music/Tantrik_Testcenter

# Create and activate the virtual environment
source .venv/bin/activate

# Upgrade pip and install requirements
pip install --upgrade pip
pip install -r requirements.txt

echo "Virtual environment setup complete."