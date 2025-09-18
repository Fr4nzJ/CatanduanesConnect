# Use Node.js as base image
FROM node:18-slim

# Install Python, pip and supervisor
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Install Flowise globally
RUN npm install -g flowise

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