import os
import json
import pandas as pd
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-2.5-flash-lite"

df = pd.read_csv("phones.csv")

# ── Step 1: Extract criteria from natural language ───────────────────────────
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
        "iphone": "Apple",
        "pixel": "Google",
        "redmi": "Xiaomi",
        "poco": "Xiaomi",
        "rog": "ASUS",
    }
    if criteria.get("brand"):
        criteria["brand"] = brand_aliases.get(criteria["brand"].lower(), criteria["brand"])

    return criteria


# ── Step 2: Clarification loop ───────────────────────────────────────────────
def check_missing_fields(criteria):
    missing = []
    if criteria.get("budget_max") is None:
        missing.append("budget")
    return missing


# ── Step 3: Filter dataset ───────────────────────────────────────────────────
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


# ── Step 4: Rank, compare, and recommend ────────────────────────────────────
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

Be concise and direct.
"""
    response = client.models.generate_content(model=MODEL, contents=prompt)
    return response.text


# ── Main agent loop ──────────────────────────────────────────────────────────
def main():
    print("=== Smartphone Selector Agent ===")
    print("Type 'reset' to start over or 'quit' to exit.\n")

    criteria = None  # persists across turns

    while True:
        if criteria is None:
            user_input = input("Tell me what you're looking for in a phone:\n> ")
        else:
            user_input = input("\nRefine your search or ask for something different:\n> ")

        if user_input.lower() == "quit":
            print("Goodbye!")
            break

        if user_input.lower() == "reset":
            criteria = None
            print("\nSearch reset. Starting fresh.\n")
            continue

        # extract and merge criteria
        print("\nAnalyzing your request...")
        criteria = extract_criteria(user_input, previous_criteria=criteria)
        print(f"Current criteria: {json.dumps(criteria, indent=2)}")

        # clarification loop
        missing = check_missing_fields(criteria)
        if missing:
            print("\nI need a bit more info.")
            if "budget" in missing:
                budget = input("What's your budget in USD?\n> ")
                criteria["budget_max"] = float(budget)

        # filter
        matches = filter_phones(criteria)

        if matches.empty:
            print("\nNo exact matches found. Relaxing spec filters and retrying...")
            matches = filter_phones(criteria, relax=True)

        if matches.empty:
            print("\nNo phones found. Try typing 'reset' or adjusting your criteria.")
            continue

        print(f"\nFound {len(matches)} matching phones. Generating recommendation...\n")

        result = rank_and_recommend(criteria, matches)
        print(result)


if __name__ == "__main__":
    main()