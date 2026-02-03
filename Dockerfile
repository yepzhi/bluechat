FROM python:3.10-slim

# Create User for Hugging Face (uid 1000)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface

WORKDIR /app

# Install Python dependencies
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy App
COPY --chown=user . .

EXPOSE 7860

CMD ["python", "app.py"]
