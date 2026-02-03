const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');
const fetch = (...args) => import('node-fetch').then(({ default: fetch }) => fetch(...args));

const app = express();
const PORT = 7860;

// Groq API Configuration
const GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions';
const GROQ_API_KEY = process.env.GROQ_API_KEY;

app.use(cors());
app.use(express.json());
app.use(express.static('.'));

// Load Knowledge Base (Bluebook)
let qaData = [];
try {
    const dataPath = path.join(__dirname, 'qa-data', 'bluebook.json');
    if (fs.existsSync(dataPath)) {
        qaData = JSON.parse(fs.readFileSync(dataPath, 'utf8'));
        console.log(`✅ Loaded ${qaData.length} Knowledge Entries from Bluebook.`);
    } else {
        console.warn('⚠️ Bluebook knowledge base not found at qa-data/bluebook.json');
    }
} catch (e) {
    console.error('❌ Error loading Knowledge Base:', e);
}

// Helper: Normalize text
function normalize(text) {
    return text.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

// Simple RAG Matcher
function findContext(query) {
    const q = normalize(query);
    const words = q.split(/\s+/).filter(w => w.length > 3);

    let bestMatch = null;
    let maxScore = 0;

    for (const item of qaData) {
        let score = 0;
        const content = normalize(item.category + " " + item.question + " " + item.answer);

        words.forEach(w => {
            if (content.includes(w)) score++;
        });

        if (score > maxScore) {
            maxScore = score;
            bestMatch = item;
        }
    }

    // Threshold to return context
    return maxScore > 0 ? bestMatch : null;
}

app.post('/api/chat', async (req, res) => {
    try {
        const { messages } = req.body;
        if (!messages || !messages.length) return res.status(400).json({ error: 'No messages' });

        const lastMsg = messages[messages.length - 1].content;
        console.log(`📝 User: ${lastMsg}`);

        // Check for Groq API Key
        if (!GROQ_API_KEY) {
            console.error('❌ GROQ_API_KEY not configured');
            return res.status(500).json({ error: 'AI service not configured. Please add GROQ_API_KEY secret.' });
        }

        // 1. RAG Lookup
        const context = findContext(lastMsg);
        let systemPrompt = `You are "BlueChat", an intelligent assistant for JovenesSTEM.
        Your source of truth is the "Bluebook v1" (Science & Technology Education).
        
        RULES:
        - Answer concisely in SPANISH (unless asked in English).
        - If the context provided helps, USE IT correctly.
        - If you don't know, say so. Do not invent.
        - Be enthusiastic about Science, STEM, and Education.`;

        if (context) {
            console.log(`💡 RAG Found: ${context.category}`);
            systemPrompt += `\n\nCONTEXT FROM BLUEBOOK:\n${context.answer}\n\nUse this context to answer the user.`;
        }

        // 2. Call Groq API
        const payload = {
            model: 'llama3-8b-8192',
            messages: [
                { role: 'system', content: systemPrompt },
                ...messages
            ],
            max_tokens: 500,
            stream: false
        };

        const response = await fetch(GROQ_API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${GROQ_API_KEY}`
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (data.error) {
            console.error('Groq API Error:', data.error);
            throw new Error(data.error.message || data.error);
        }

        if (!data.choices || !data.choices[0] || !data.choices[0].message) {
            console.error('Invalid Groq response:', JSON.stringify(data));
            throw new Error('Invalid response from AI service');
        }

        const aiText = data.choices[0].message.content;
        console.log(`🤖 AI: ${aiText.substring(0, 30)}...`);

        res.json({
            content: [{ text: aiText }],
            source: context ? 'bluebook-rag' : 'qwen-general'
        });

    } catch (error) {
        console.error('SERVER ERROR:', error);
        res.status(500).json({ error: 'Internal AI Error' });
    }
});

app.listen(PORT, '0.0.0.0', () => {
    console.log(`🚀 BlueChat Server running on port ${PORT}`);
    console.log(`🔑 Groq API Key: ${GROQ_API_KEY ? 'Configured ✅' : 'NOT CONFIGURED ❌'}`);
});
