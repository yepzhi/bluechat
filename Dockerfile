# Use Ubuntu to facilitate Ollama installation
FROM ubuntu:22.04

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies (Curl for Ollama, Node.js)
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Setup Working Directory
WORKDIR /app

# Copy application files
COPY package.json .
# Install Node dependencies
RUN npm install

COPY . .

# Set permissions for entrypoint
RUN chmod +x entrypoint.sh

# Expose port 7860 (Hugging Face default)
EXPOSE 7860

# Start script
CMD ["./entrypoint.sh"]
