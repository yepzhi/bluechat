from flask import Flask, request, jsonify, send_from_directory
import json
import os
import unicodedata
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

app = Flask(__name__, static_folder='.')

# ============ Load Qwen Model ============
print("🦙 Loading Qwen2.5-1.5B-Instruct model... (this may take a few minutes)")
MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.float32,  # CPU compatible
    device_map="auto",
    trust_remote_code=True,
    low_cpu_mem_usage=True
)
print("✅ Model loaded successfully!")

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
    """Generate response using Qwen"""
    system_prompt = """You are "BlueChat", an intelligent assistant for JovenesSTEM.
Your source of truth is the "Bluebook v1" (Science & Technology Education).

RULES:
- Answer concisely in SPANISH (unless asked in English).
- If the context provided helps, USE IT correctly.
- If you don't know, say so. Do not invent.
- Be enthusiastic about Science, STEM, and Education."""

    if context:
        system_prompt += f"\n\nCONTEXT FROM BLUEBOOK:\n{context['answer']}\n\nUse this context to answer the user."
    
    # Build conversation for Qwen
    conversation = [{"role": "system", "content": system_prompt}]
    for msg in messages:
        conversation.append({"role": msg["role"], "content": msg["content"]})
    
    # Apply chat template
    text = tokenizer.apply_chat_template(
        conversation,
        tokenize=False,
        add_generation_prompt=True
    )
    
    # Tokenize and generate
    inputs = tokenizer([text], return_tensors="pt").to(model.device)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=512,
            temperature=0.7,
            top_p=0.9,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id
        )
    
    # Decode response
    generated_ids = outputs[0][inputs.input_ids.shape[1]:]
    response = tokenizer.decode(generated_ids, skip_special_tokens=True)
    
    return response.strip()

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
        
        # Generate response
        ai_text = generate_response(messages, context)
        print(f"🤖 AI: {ai_text[:50]}...")
        
        return jsonify({
            "content": [{"text": ai_text}],
            "source": "bluebook-rag" if context else "qwen-local"
        })
        
    except Exception as e:
        print(f"SERVER ERROR: {e}")
        return jsonify({"error": "Internal AI Error"}), 500

# ============ Main ============
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7860)
