#!/bin/sh

# Find all JS files and replace the default URL
find /usr/share/nginx/html/assets -type f -name "*.js" -print0 | xargs -0 sed -i "s|http://default-backend-url|$BACKEND_URL|g"

# Replace placeholders in the Nginx configuration with environment variables
envsubst '${BACKEND_URL}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf

# Optional: print replaced URLs for debugging
echo "Replaced default URL with: $BACKEND_URL"

# Optional: print replaced URLs for debugging
echo "Replaced 2 default URL with: ${BACKEND_URL}"

# Start Nginx
exec "$@"
