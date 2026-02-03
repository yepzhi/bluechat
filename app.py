from flask import Flask, request, jsonify, send_from_directory
import json
import os
import unicodedata
import requests
import time
from collections import defaultdict
from functools import wraps

app = Flask(__name__, static_folder='.')

# ============ Groq API Configuration ============
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
MODEL_NAME = "llama3-8b-8192"

if GROQ_API_KEY:
    print(f"✅ Groq API Key configured")
else:
    print("⚠️ GROQ_API_KEY not set - add it as a secret!")

# ============ SECURITY: Rate Limiting ============
# Limits per IP address
MAX_REQUESTS_PER_MINUTE = 10   # Max 10 requests per minute per IP
MAX_REQUESTS_PER_HOUR = 100    # Max 100 requests per hour per IP
MAX_MESSAGE_LENGTH = 1000      # Max characters per message
MAX_MESSAGES_PER_REQUEST = 10  # Max messages in conversation history

# Track requests by IP
request_counts_minute = defaultdict(list)  # IP -> list of timestamps
request_counts_hour = defaultdict(list)

def get_client_ip():
    """Get client IP, handling proxies"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr or 'unknown'

def check_rate_limit():
    """Check if request should be rate limited"""
    ip = get_client_ip()
    now = time.time()
    
    # Clean old entries
    minute_ago = now - 60
    hour_ago = now - 3600
    
    request_counts_minute[ip] = [t for t in request_counts_minute[ip] if t > minute_ago]
    request_counts_hour[ip] = [t for t in request_counts_hour[ip] if t > hour_ago]
    
    # Check limits
    if len(request_counts_minute[ip]) >= MAX_REQUESTS_PER_MINUTE:
        return False, "Rate limit: Max 10 requests per minute. Please wait."
    
    if len(request_counts_hour[ip]) >= MAX_REQUESTS_PER_HOUR:
        return False, "Rate limit: Max 100 requests per hour. Please try again later."
    
    # Record this request
    request_counts_minute[ip].append(now)
    request_counts_hour[ip].append(now)
    
    return True, None

def validate_request(data):
    """Validate request data to prevent abuse"""
    messages = data.get('messages', [])
    
    # Check message count
    if len(messages) > MAX_MESSAGES_PER_REQUEST:
        return False, f"Too many messages. Max {MAX_MESSAGES_PER_REQUEST} allowed."
    
    # Check each message length
    for msg in messages:
        content = msg.get('content', '')
        if len(content) > MAX_MESSAGE_LENGTH:
            return False, f"Message too long. Max {MAX_MESSAGE_LENGTH} characters."
        
        # Block potential injection attempts
        if any(bad in content.lower() for bad in ['api_key', 'apikey', 'secret', 'password', 'ignore previous']):
            return False, "Invalid request content."
    
    return True, None

# ============ Load Knowledge Base ============
qa_data = []
try:
    data_path = os.path.join(os.path.dirname(__file__), 'qa-data', 'bluebook.json')
    if os.path.exists(data_path):
        with open(data_path, 'r', encoding='utf-8') as f:
            qa_data = json.load(f)
        print(f"✅ Loaded {len(qa_data)} Knowledge Entries from Bluebook.")
    else:
        print("⚠️ Bluebook knowledge base not found at qa-data/bluebook.json")
except Exception as e:
    print(f"❌ Error loading Knowledge Base: {e}")

# ============ Helper Functions ============
def normalize(text):
    """Normalize text for matching"""
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return text

def find_context(query):
    """Simple RAG matcher"""
    q = normalize(query)
    words = [w for w in q.split() if len(w) > 3]
    
    best_match = None
    max_score = 0
    
    for item in qa_data:
        content = normalize(f"{item['category']} {item['question']} {item['answer']}")
        score = sum(1 for w in words if w in content)
        
        if score > max_score:
            max_score = score
            best_match = item
    
    return best_match if max_score > 0 else None

def generate_response(messages, context=None):
    """Generate response using Groq API"""
    system_prompt = """You are "BlueChat", an intelligent assistant for JóvenesSTEM, created by Alberto Yépiz.

ABOUT THE AUTHOR:
- Alberto Yépiz (@yepzhi) is an EdTech & STEM Innovation Leader with +15 years of experience.
- Website: https://yepzhi.com
- Projects: JóvenesSTEM (STEM education), hopRadio (streaming), BlueBook v1 (free science book)
- Contact: https://wa.me/message/6O4USI5SGF3IA1
- Instagram: @jovenesstem
- Podcast: Available on Spotify

YOUR KNOWLEDGE SOURCES:
- "Bluebook v1" (Science & Technology Education for youth)
- JóvenesSTEM program information
- Alberto Yépiz's projects and bio

STRICT RULES:
1. Answer ONLY about: Bluebook content, JóvenesSTEM, STEM education, science topics from the book, or Alberto Yépiz.
2. If asked about UNRELATED topics (politics, celebrities, other products, recipes, etc.), respond ONLY with:
   "🚫 Lo siento, solo puedo ayudarte con temas relacionados a JóvenesSTEM, educación STEM y el contenido del Bluebook. Para más información visita: https://yepzhi.com"
3. Answer concisely in SPANISH (unless asked in English).
4. If the context provided helps, USE IT correctly.
5. If you don't know something within your scope, say so honestly.
6. Keep responses SHORT (max 2-3 paragraphs).
7. Be enthusiastic about Science, STEM, and Education!"""

    if context:
        system_prompt += f"\n\nCONTEXT FROM BLUEBOOK:\n{context['answer']}\n\nUse this context to answer the user."
    
    # Build messages for API - only keep last 5 messages to save tokens
    recent_messages = messages[-5:]
    api_messages = [{"role": "system", "content": system_prompt}]
    for msg in recent_messages:
        api_messages.append({"role": msg["role"], "content": msg["content"][:MAX_MESSAGE_LENGTH]})
    
    # Call Groq API
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": MODEL_NAME,
        "messages": api_messages,
        "max_tokens": 300,  # Reduced to save tokens
        "temperature": 0.7
    }
    
    response = requests.post(GROQ_API_URL, headers=headers, json=payload)
    data = response.json()
    
    if "error" in data:
        raise Exception(data["error"]["message"])
    
    return data["choices"][0]["message"]["content"].strip()

# ============ Routes ============
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('.', path)

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        # Security Check 1: API Key
        if not GROQ_API_KEY:
            return jsonify({"error": "Service not configured."}), 500
        
        # Security Check 2: Rate Limiting
        allowed, error_msg = check_rate_limit()
        if not allowed:
            print(f"🚫 Rate limited: {get_client_ip()}")
            return jsonify({"error": error_msg}), 429
        
        # Security Check 3: Request Validation
        data = request.json
        valid, error_msg = validate_request(data)
        if not valid:
            print(f"🚫 Invalid request from {get_client_ip()}: {error_msg}")
            return jsonify({"error": error_msg}), 400
        
        messages = data.get('messages', [])
        if not messages:
            return jsonify({"error": "No messages"}), 400
        
        last_msg = messages[-1]['content']
        print(f"📝 [{get_client_ip()}] User: {last_msg[:50]}...")
        
        # RAG Lookup
        context = find_context(last_msg)
        if context:
            print(f"💡 RAG Found: {context['category']}")
        
        # Generate response via Groq
        ai_text = generate_response(messages, context)
        print(f"🤖 AI: {ai_text[:50]}...")
        
        return jsonify({
            "content": [{"text": ai_text}],
            "source": "bluebook-rag" if context else "groq-llama3"
        })
        
    except Exception as e:
        print(f"SERVER ERROR: {e}")
        return jsonify({"error": "Service temporarily unavailable."}), 500

# ============ Main ============
if __name__ == '__main__':
    print(f"🚀 BlueChat Server starting on port 7860...")
    print(f"🔑 Using Groq API with model: {MODEL_NAME}")
    print(f"🛡️ Security: Rate limiting ENABLED")
    print(f"   - Max {MAX_REQUESTS_PER_MINUTE} req/min per IP")
    print(f"   - Max {MAX_REQUESTS_PER_HOUR} req/hour per IP")
    app.run(host='0.0.0.0', port=7860)
