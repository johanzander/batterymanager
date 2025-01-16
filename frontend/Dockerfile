FROM node:18-alpine AS build

WORKDIR /app

COPY package*.json ./

RUN npm ci

COPY . .

# Print the build-time API URL
ARG VITE_API_URL=https://battery-backend-3pukyai4lq-ew.a.run.app
#ARG VITE_API_URL=http://default-backend-url
ENV VITE_API_URL=$VITE_API_URL
RUN echo "Building with VITE_API_URL: $VITE_API_URL"

# Print the build-time API URL
ARG BACKEND_URL=https://battery-backend-3pukyai4lq-ew.a.run.app
ENV BACKEND_URL=$BACKEND_URL
RUN echo "Building with BACKEND_URL: $BACKEND_URL"

RUN npm run build

FROM nginx:alpine

# Print the build-time API URL
ARG VITE_API_URL=https://battery-backend-3pukyai4lq-ew.a.run.app
#ARG VITE_API_URL=http://default-backend-url
ENV VITE_API_URL=$VITE_API_URL
RUN echo "Building with VITE_API_URL: $VITE_API_URL"

# Print the build-time API URL
ARG BACKEND_URL=https://battery-backend-3pukyai4lq-ew.a.run.app
ENV BACKEND_URL=$BACKEND_URL
RUN echo "Building with BACKEND_URL: $BACKEND_URL"

# Copy nginx configuration
COPY nginx.conf /etc/nginx/templates/default.conf.template

# Copy built assets from the build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Add a script to verify and replace URLs
COPY replace-env-vars.sh /docker-entrypoint.d/40-replace-env-vars.sh
RUN chmod +x /docker-entrypoint.d/40-replace-env-vars.sh

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]