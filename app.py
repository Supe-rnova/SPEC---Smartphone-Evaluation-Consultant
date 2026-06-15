import os
import json
import pandas as pd
from dotenv import load_dotenv
from google import genai
from flask import Flask, request, jsonify, session
from flask import render_template_string

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-2.5-flash-lite"
df = pd.read_csv("phones.csv")

app = Flask(__name__)
app.secret_key = os.urandom(24)  # needed for session storage


# ── Agent functions (same as agent.py) ──────────────────────────────────────
def extract_criteria(user_input, previous_criteria=None):
    prev = json.dumps(previous_criteria, indent=2) if previous_criteria else "None"
    prompt = f"""
You are a smartphone shopping assistant. Extract search criteria from the user's message.
If previous criteria exist, merge the new message on top — keep previous values unless the user explicitly changes them.

Return ONLY a JSON object with these fields (use null if not mentioned and no previous value exists):
- budget_max (number in USD)
- brand (string)
- min_ram_gb (number)
- min_storage_gb (number)
- min_battery_mah (number)
- min_camera_mp (number)
- color (string)
- use_case (string: budget/everyday/gaming/photography/productivity)
- five_g (true/false/null)
- wireless_charging (true/false/null)
- nfc (true/false/null)
- max_weight_grams (number)
- min_refresh_rate_hz (number)
- min_fast_charge_watts (number)
- water_resistance (true/false/null)
- min_camera_count (number)
- os (string: Android/iOS/null)

Previous criteria: {prev}
New user message: "{user_input}"

Return only the JSON, no explanation, no markdown.
"""
    response = client.models.generate_content(model=MODEL, contents=prompt)
    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    criteria = json.loads(raw.strip())

    brand_aliases = {
        "iphone": "Apple", "pixel": "Google",
        "redmi": "Xiaomi", "poco": "Xiaomi", "rog": "ASUS",
    }
    if criteria.get("brand"):
        criteria["brand"] = brand_aliases.get(criteria["brand"].lower(), criteria["brand"])

    return criteria


def filter_phones(criteria, relax=False):
    result = df.copy()
    if criteria.get("budget_max"):
        result = result[result["price_usd"] <= criteria["budget_max"]]
    if criteria.get("brand"):
        result = result[result["brand"].str.lower() == criteria["brand"].lower()]
    if criteria.get("color"):
        result = result[result["color"].str.lower().str.contains(criteria["color"].lower())]
    if criteria.get("use_case"):
        result = result[result["use_case"].str.lower() == criteria["use_case"].lower()]
    if criteria.get("os"):
        result = result[result["os"].str.lower().str.contains(criteria["os"].lower())]
    if criteria.get("five_g") is True:
        result = result[result["five_g"] == True]
    if criteria.get("wireless_charging") is True:
        result = result[result["wireless_charging"] == True]
    if criteria.get("nfc") is True:
        result = result[result["nfc"] == True]
    if criteria.get("water_resistance") is True:
        result = result[result["water_resistance"] != "No"]
    if not relax:
        if criteria.get("min_ram_gb"):
            result = result[result["ram_gb"] >= criteria["min_ram_gb"]]
        if criteria.get("min_storage_gb"):
            result = result[result["storage_gb"] >= criteria["min_storage_gb"]]
        if criteria.get("min_battery_mah"):
            result = result[result["battery_mah"] >= criteria["min_battery_mah"]]
        if criteria.get("min_camera_mp"):
            result = result[result["camera_mp"] >= criteria["min_camera_mp"]]
        if criteria.get("min_refresh_rate_hz"):
            result = result[result["refresh_rate_hz"] >= criteria["min_refresh_rate_hz"]]
        if criteria.get("min_fast_charge_watts"):
            result = result[result["fast_charge_watts"] >= criteria["min_fast_charge_watts"]]
        if criteria.get("max_weight_grams"):
            result = result[result["weight_grams"] <= criteria["max_weight_grams"]]
        if criteria.get("min_camera_count"):
            result = result[result["camera_count"] >= criteria["min_camera_count"]]
    return result


def rank_and_recommend(criteria, matches):
    phones_text = matches.to_string(index=False)
    prompt = f"""
You are a smartphone expert. A user is looking for a phone with these criteria:
{json.dumps(criteria, indent=2)}

Here are the matching phones:
{phones_text}

Do the following:
1. Pick the top 3 phones and briefly explain why each made the shortlist (1-2 sentences each)
2. Give a side-by-side comparison of the top 3 as a simple table
3. Give a final recommendation with clear reasoning

Be concise and direct. Use markdown formatting.
"""
    response = client.models.generate_content(model=MODEL, contents=prompt)
    return response.text


# ── HTML template ────────────────────────────────────────────────────────────
HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smartphone Selector</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f0f2f5; height: 100vh; display: flex; flex-direction: column; }
        header { background: #1a1a2e; color: white; padding: 16px 24px; font-size: 1.2rem; font-weight: 600; }
        header span { color: #7c83fd; }
        #chat { flex: 1; overflow-y: auto; padding: 24px; display: flex; flex-direction: column; gap: 16px; }
        .bubble { max-width: 75%; padding: 12px 16px; border-radius: 16px; line-height: 1.6; font-size: 0.95rem; }
        .user { align-self: flex-end; background: #7c83fd; color: white; border-bottom-right-radius: 4px; }
        .agent { align-self: flex-start; background: white; color: #1a1a2e; border-bottom-left-radius: 4px; box-shadow: 0 1px 4px rgba(0,0,0,0.1); }
        .agent table { border-collapse: collapse; margin: 12px 0; width: 100%; font-size: 0.85rem; }
        .agent th, .agent td { border: 1px solid #ddd; padding: 6px 10px; text-align: left; }
        .agent th { background: #f5f5f5; font-weight: 600; }
        #input-area { display: flex; gap: 10px; padding: 16px 24px; background: white; border-top: 1px solid #e0e0e0; }
        #msg { flex: 1; padding: 10px 14px; border: 1px solid #ddd; border-radius: 24px; font-size: 0.95rem; outline: none; }
        #msg:focus { border-color: #7c83fd; }
        #send-btn { padding: 10px 20px; background: #7c83fd; color: white; border: none; border-radius: 24px; cursor: pointer; font-size: 0.95rem; font-weight: 500; }
        #send-btn:hover { background: #6370fc; }
        #reset-btn { padding: 10px 20px; background: #e0e0e0; color: #555; border: none; border-radius: 24px; cursor: pointer; font-size: 0.95rem; }
        #reset-btn:hover { background: #ccc; }
    </style>
</head>
<body>
    <header>📱 <span>Smartphone</span> Selector Agent</header>
    <div id="chat">
        <div class="bubble agent">Hi! Tell me what you're looking for in a phone — budget, brand, use case, specs, anything. I'll find the best options for you.</div>
    </div>
    <div id="input-area">
        <input id="msg" type="text" placeholder="e.g. I want a gaming phone under $700 with 5G..." />
        <button id="send-btn">Send</button>
        <button id="reset-btn">Reset</button>
    </div>

    <script>
        const chat = document.getElementById("chat");
        const msg = document.getElementById("msg");

        document.getElementById("send-btn").addEventListener("click", send);
        document.getElementById("reset-btn").addEventListener("click", reset);

        msg.addEventListener("keydown", function(e) { if (e.key === "Enter") send(); });

        function addBubble(text, role) {
            const div = document.createElement("div");
            div.className = "bubble " + role;
            if (role === "agent") {
                div.innerHTML = marked.parse(text);
            } else {
                div.textContent = text;
            }
            chat.appendChild(div);
            chat.scrollTop = chat.scrollHeight;
            return div;
        }

        async function send() {
            const text = msg.value.trim();
            if (!text) return;
            msg.value = "";
            addBubble(text, "user");
            const thinking = addBubble("Thinking...", "agent");

            const res = await fetch("/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: text })
            });
            const data = await res.json();
            thinking.remove();
            addBubble(data.message, "agent");
        }

        async function reset() {
            await fetch("/reset", { method: "POST" });
            chat.innerHTML = '<div class="bubble agent">Search reset! Tell me what you are looking for in a phone.</div>';
        }
    </script>
</body>
</html>
"""


# ── Flask routes ─────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_input = data.get("message", "").strip()

    # retrieve criteria from session
    criteria = session.get("criteria", None)

    # handle pending budget response
    if session.get("needs_budget"):
        try:
            criteria["budget_max"] = float(user_input.replace("$", "").replace(",", ""))
            session["needs_budget"] = False
        except ValueError:
            return jsonify({"message": "Please enter a valid budget amount, e.g. 500"})

    else:
        criteria = extract_criteria(user_input, previous_criteria=criteria)

        if criteria.get("budget_max") is None:
            session["criteria"] = criteria
            session["needs_budget"] = True
            return jsonify({"message": "What's your budget in USD?", "needs_budget": True})

    session["criteria"] = criteria

    matches = filter_phones(criteria)
    relaxed = False

    if matches.empty:
        matches = filter_phones(criteria, relax=True)
        relaxed = True

    if matches.empty:
        return jsonify({"message": "No phones found matching your criteria. Try adjusting your budget, brand, or specs."})

    result = rank_and_recommend(criteria, matches)

    prefix = f"*No exact matches — showing closest results with relaxed spec filters.*\n\n" if relaxed else ""
    count_note = f"Found **{len(matches)} matching phones**. Here are the top picks:\n\n"

    return jsonify({"message": prefix + count_note + result})


@app.route("/reset", methods=["POST"])
def reset():
    session.clear()
    return jsonify({"status": "reset"})


if __name__ == "__main__":
    app.run(debug=True)