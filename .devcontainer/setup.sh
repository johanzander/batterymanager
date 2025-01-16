#!/bin/bash

# Install nvm if not already installed
if [ ! -d "/usr/local/share/nvm" ]; then
  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.3/install.sh | bash
fi

# Source nvm script
export NVM_DIR="/usr/local/share/nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"

# Install and use the desired Node.js version
nvm install node
nvm use node

# Ensure npm is available
export PATH="$NVM_DIR/versions/node/$(nvm version)/bin:$PATH"

# Install project dependencies
cd /workspaces/batterymanager/frontend
npm install

# Install Python dependencies
cd /workspaces/batterymanager/backend
pip install --upgrade pip
pip3 install --user -r requirements.txt