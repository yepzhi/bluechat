FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV OLLAMA_HOST=0.0.0.0

# 1. Install Basics + Node.js 20
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update && apt-get install -y nodejs zstd \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Ollama Binary Manually (It is a binary, not a TGZ)
RUN curl -L https://ollama.com/download/ollama-linux-amd64 -o /usr/local/bin/ollama \
    && chmod +x /usr/local/bin/ollama

# 3. Create User for Hugging Face (uid 1000)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR /app

# 4. Copy & Install Deps
COPY --chown=user package.json .
RUN npm install

# 5. Copy App
COPY --chown=user . .
RUN chmod +x entrypoint.sh

EXPOSE 7860

CMD ["./entrypoint.sh"]
