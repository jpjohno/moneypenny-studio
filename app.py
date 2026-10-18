from flask import Flask, render_template_string, request, jsonify
import requests
import re

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>MoneyPenny Enterprise AI Studio</title>
    <style>
        :root {
            --bg-base: #030712;
            --bg-panel: #0b0f19;
            --border: #1f293d;
            --accent: #38bdf8;
            --accent-glow: rgba(56, 189, 248, 0.2);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --action-color: #f43f5e;
        }
        body { background: var(--bg-base); color: var(--text-main); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; display: flex; height: 100vh; margin: 0; overflow: hidden; }
        
        .sidebar { width: 380px; background: var(--bg-panel); border-right: 1px solid var(--border); display: flex; flex-direction: column; padding: 20px; box-sizing: border-box; overflow-y: auto; }
        .sidebar::-webkit-scrollbar { width: 6px; }
        .sidebar::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
        
        h2 { color: var(--accent); font-size: 1.2rem; margin-top: 0; display: flex; align-items: center; gap: 8px; }
        .section-title { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; color: var(--text-muted); margin: 15px 0 5px 0; font-weight: bold; }
        
        label { font-size: 0.85rem; color: var(--text-muted); display: block; margin-top: 8px; }
        select, textarea, input[type="text"], input[type="file"], input[type="range"] { width: 100%; background: #131b2e; border: 1px solid var(--border); color: #fff; padding: 10px; border-radius: 8px; margin-top: 4px; box-sizing: border-box; font-size: 0.9rem; }
        textarea { resize: vertical; height: 70px; }
        .slider-row { display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem; color: var(--text-muted); margin-top: 8px; }
        .slider-val { color: var(--accent); font-weight: bold; }

        button { background: linear-gradient(135deg, #0284c7, #0369a1); color: white; border: none; padding: 12px; border-radius: 8px; font-weight: bold; cursor: pointer; margin-top: 15px; width: 100%; transition: opacity 0.2s; box-shadow: 0 4px 12px var(--accent-glow); }
        button:hover { opacity: 0.9; }

        .main-stage { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 20px; position: relative; background: radial-gradient(circle at center, #0f172a 0%, var(--bg-base) 100%); }
        
        .stage-box { width: 420px; height: 480px; background: var(--bg-panel); border-radius: 24px; border: 1px solid var(--border); display: flex; flex-direction: column; align-items: center; justify-content: center; position: relative; box-shadow: 0 30px 60px rgba(0,0,0,0.7); overflow: hidden; }
        
        /* Advanced Photo Animator CSS */
        .avatar-canvas { width: 100%; height: 100%; object-fit: cover; transition: transform 0.6s cubic-bezier(0.25, 1, 0.5, 1), filter 0.3s ease; }
        .anim-lean-in { transform: scale(1.08) translateY(-8px); filter: contrast(1.05); }
        .anim-tilt-head { transform: scale(1.04) rotate(-3deg); }
        .anim-whisper { transform: scale(1.12) translateY(-12px); filter: brightness(0.95); }
        .speaking-pulse { animation: speechGlow 0.6s infinite alternate; }
        @keyframes speechGlow {
            0% { filter: brightness(1); }
            100% { filter: brightness(1.18) saturate(1.1); }
        }
        
        .chat-card { width: 700px; background: var(--bg-panel); border: 1px solid var(--border); border-radius: 14px; padding: 20px; margin-top: 20px; box-sizing: border-box; box-shadow: 0 10px 30px rgba(0,0,0,0.4); }
        .action-text { color: var(--action-color); font-style: italic; font-size: 0.95rem; margin-bottom: 6px; min-height: 22px; }
        .dialogue-text { color: var(--text-main); font-size: 1.15rem; font-weight: 500; line-height: 1.5; }
        
        .status-badge { display: inline-block; width: 8px; height: 8px; background: #22c55e; border-radius: 50%; box-shadow: 0 0 8px #22c55e; margin-right: 6px; }
    </style>
</head>
<body>
    <div class="sidebar">
        <h2><span class="status-badge"></span> Enterprise Studio</h2>
        
        <div class="section-title">Model & Character</div>
        <label>Active Engine / Model</label>
        <select id="modelSelect">
            <option value="slutbags">slutbags (Uncensored 3B)</option>
            <option value="MoneyPenny">MoneyPenny</option>
        </select>

        <label>Upload Character Portrait</label>
        <input type="file" id="photoUpload" accept="image/*" onchange="loadPhoto(event)">

        <div class="section-title">Advanced Parameters</div>
        <label>System Prompt / Personality Override</label>
        <textarea id="systemPrompt">You are MoneyPenny, sharp-witted and flirtatious. Always interweave physical actions and expressions inside asterisks (*action*), followed by your spoken dialogue in quotation marks ("speech").</textarea>

        <div class="slider-row">
            <span>Temperature</span>
            <span class="slider-val" id="tempVal">0.75</span>
        </div>
        <input type="range" id="tempRange" min="0.1" max="1.5" step="0.05" value="0.75" oninput="document.getElementById('tempVal').innerText=this.value">

        <div class="slider-row">
            <span>Max Tokens</span>
            <span class="slider-val" id="tokenVal">256</span>
        </div>
        <input type="range" id="tokenRange" min="64" max="1024" step="32" value="256" oninput="document.getElementById('tokenVal').innerText=this.value">

        <div class="section-title">Interaction</div>
        <label>Your Message</label>
        <textarea id="userInput" style="height: 60px;">Hello, tell me something interesting.</textarea>
        <button onclick="sendPrompt()">Generate Response & Animate</button>
    </div>

    <div class="main-stage">
        <div class="stage-box">
            <img id="avatarImage" class="avatar-canvas" src="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=600&auto=format&fit=crop&q=80" alt="Avatar">
        </div>

        <div class="chat-card">
            <div class="action-text" id="actionDisplay">*Studio initialized. Ready for prompt execution.*</div>
            <div class="dialogue-text" id="dialogueDisplay">Type a message on the left to begin session.</div>
        </div>
    </div>

    <script>
        function loadPhoto(event) {
            const reader = new FileReader();
            reader.onload = function(){
                document.getElementById('avatarImage').src = reader.result;
            }
            reader.readAsDataURL(event.target.files[0]);
        }

        async function sendPrompt() {
            const prompt = document.getElementById('userInput').value;
            const model = document.getElementById('modelSelect').value;
            const system = document.getElementById('systemPrompt').value;
            const temperature = parseFloat(document.getElementById('tempRange').value);
            const max_tokens = parseInt(document.getElementById('tokenRange').value);

            document.getElementById('actionDisplay').innerText = "*Processing local inference...*";
            document.getElementById('dialogueDisplay').innerText = "...";

            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt, model, system, temperature, max_tokens })
            });
            const data = await response.json();
            
            document.getElementById('actionDisplay').innerText = data.actions ? `*${data.actions}*` : "";
            document.getElementById('dialogueDisplay').innerText = `"${data.dialogue}"`;

            // Drive photo animation and speech synchronously
            animateAvatarBasedOnActions(data.actions);
            speakDialogue(data.dialogue);
        }

        function animateAvatarBasedOnActions(actionText) {
            const avatar = document.getElementById('avatarImage');
            const text = actionText.toLowerCase();
            
            avatar.className = "avatar-canvas"; // reset
            
            if(text.includes('lean') || text.includes('closer') || text.includes('step')) {
                avatar.classList.add('anim-lean-in');
            } else if(text.includes('whisper') || text.includes('drop')) {
                avatar.classList.add('anim-whisper');
            } else {
                avatar.classList.add('anim-tilt-head');
            }

            setTimeout(() => {
                avatar.className = "avatar-canvas";
            }, 4000);
        }

        function speakDialogue(text) {
            if ('speechSynthesis' in window) {
                window.speechSynthesis.cancel();
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.pitch = 1.0;
                utterance.rate = 1.0;
                
                const voices = window.speechSynthesis.getVoices();
                const ukVoice = voices.find(v => v.lang === 'en-GB' || v.name.includes('UK') || v.name.includes('British'));
                if (ukVoice) utterance.voice = ukVoice;

                const avatar = document.getElementById('avatarImage');
                utterance.onstart = () => avatar.classList.add('speaking-pulse');
                utterance.onend = () => avatar.classList.remove('speaking-pulse');

                window.speechSynthesis.speak(utterance);
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    prompt = data.get('prompt', '')
    model_name = data.get('model', 'slutbags')
    system_prompt = data.get('system', '')
    temperature = data.get('temperature', 0.75)
    max_tokens = data.get('max_tokens', 256)

    full_prompt = f"{system_prompt}\n\nUser: {prompt}\nMoneyPenny:"

    try:
        ollama_res = requests.post('http://localhost:11434/api/generate', json={
            "model": model_name,
            "prompt": full_prompt,
            "options": {
                "temperature": temperature,
            },
            "stream": False
        })
        raw_output = ollama_res.json().get('response', '')
    except Exception as e:
        raw_output = f'*studies you closely* "Connection error with local backend: {str(e)}"'

    # Bulletproof Parser: Extract actions (*...*) and speech ("...")
    actions = " ".join(re.findall(r'\*(.*?)\*', raw_output))
    dialogue_matches = re.findall(r'"([^"]*)"', raw_output)
    
    if dialogue_matches:
        dialogue = " ".join(dialogue_matches)
    else:
        # Fallback if quotes are missing: strip out actions and treat remaining text as dialogue
        dialogue = re.sub(r'\*.*?\*', '', raw_output).strip()
        if not dialogue:
            dialogue = raw_output

    if not actions:
        actions = "maintains an intense, focused gaze"

    return jsonify({"actions": actions, "dialogue": dialogue, "raw": raw_output})

if __name__ == '__main__':
    print("🚀 Starting Enterprise Studio at http://localhost:8090")
    app.run(port=8090, debug=False)
