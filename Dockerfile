FROM node:20-slim

# Create User for Hugging Face (uid 1000)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR /app

# Copy & Install Deps
COPY --chown=user package.json .
RUN npm install

# Copy App
COPY --chown=user . .

EXPOSE 7860

CMD ["npm", "start"]
