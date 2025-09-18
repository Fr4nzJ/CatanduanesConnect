# Use Node.js as base image
FROM node:18-bullseye-slim

# Install Python, pip, supervisor and build dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    supervisor \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Flowise with increased network timeout and better Node.js settings
ENV NODE_OPTIONS="--max-old-space-size=4096"
RUN npm config set network-timeout 1000000 && \
    npm install -g flowise --unsafe-perm=true

# Set working directory
WORKDIR /app

# Copy application files
COPY . .

# Install Python dependencies
RUN pip3 install -r requirements.txt

# Copy supervisor configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose the port that Railway will assign
ENV PORT=8080

# Start both services using supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]