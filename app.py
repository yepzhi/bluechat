from flask import Flask, request, jsonify, send_from_directory
import json
import os
import unicodedata
import requests

app = Flask(__name__, static_folder='.')

# ============ Groq API Configuration ============
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
MODEL_NAME = "llama3-8b-8192"

if GROQ_API_KEY:
    print(f"✅ Groq API Key configured")
else:
    print("⚠️ GROQ_API_KEY not set - add it as a secret!")

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
    system_prompt = """You are "BlueChat", an intelligent assistant for JovenesSTEM.
Your source of truth is the "Bluebook v1" (Science & Technology Education).

RULES:
- Answer concisely in SPANISH (unless asked in English).
- If the context provided helps, USE IT correctly.
- If you don't know, say so. Do not invent.
- Be enthusiastic about Science, STEM, and Education."""

    if context:
        system_prompt += f"\n\nCONTEXT FROM BLUEBOOK:\n{context['answer']}\n\nUse this context to answer the user."
    
    # Build messages for API
    api_messages = [{"role": "system", "content": system_prompt}]
    for msg in messages:
        api_messages.append({"role": msg["role"], "content": msg["content"]})
    
    # Call Groq API
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": MODEL_NAME,
        "messages": api_messages,
        "max_tokens": 500,
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
        if not GROQ_API_KEY:
            return jsonify({"error": "GROQ_API_KEY not configured. Add it as a secret."}), 500
        
        data = request.json
        messages = data.get('messages', [])
        
        if not messages:
            return jsonify({"error": "No messages"}), 400
        
        last_msg = messages[-1]['content']
        print(f"📝 User: {last_msg}")
        
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
        return jsonify({"error": str(e)}), 500

# ============ Main ============
if __name__ == '__main__':
    print(f"🚀 BlueChat Server starting on port 7860...")
    print(f"🔑 Using Groq API with model: {MODEL_NAME}")
    app.run(host='0.0.0.0', port=7860)
