#!/bin/sh

# Print out the PORT for debugging
echo "Starting Nginx on PORT: ${PORT:-8080}"

# Ensure the port is used
PORT=${PORT:-8080}
sed -i "s/listen 80;/listen $PORT;/" /etc/nginx/conf.d/default.conf

# Start Nginx
nginx -g "daemon off;"