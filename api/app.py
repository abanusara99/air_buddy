import os
import requests
from flask import Flask, request, jsonify, render_template
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ------------------------------------------------------------
# Fix for TemplateNotFound: tell Flask where templates/static
# live relative to this file (they are one level up in api/..)
# ------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

MODEL = "openrouter/free"

SYSTEM_PROMPT = (
    "You are AirBuddy, a friendly air-quality assistant for families. "
    "Based on the user's AQI, location, and household situation, give simple, warm, "
    "and actionable advice about indoor air quality, low-emission routines, and "
    "sustainable alternatives. Reply in concise, natural English. "
    "Do not invent AQI numbers; only explain and advise."
)

# ============================================================
# CITY DATA — edit this dictionary to add or remove cities
# ============================================================
CITY_DATA = {
    "USA": [
        "Los Angeles", "Visalia", "Bakersfield", "Phoenix",
        "Houston", "Denver", "Detroit", "New York"
    ],
    "India": [
        "Kolkata", "Delhi", "Mumbai", "Chennai", "Bengaluru"
    ],
    "China": [
        "Beijing", "Chengdu", "Chongqing", "Shanghai",
        "Guangzhou", "Shijiazhuang"
    ],
    "Japan": [
        "Tokyo", "Yokohama", "Osaka", "Nagoya", "Sapporo", "Fukuoka"
    ],
    "Europe": [
        "Athens", "Bucharest", "Milan", "Warsaw",
        "Prague", "Copenhagen", "Stockholm"
    ],
    "Africa": [
        "Dakar", "Johannesburg", "Cape Town", "Pretoria"
    ],
}

REGIONS = list(CITY_DATA.keys())


@app.route("/")
def home():
    return render_template("index.html", regions=REGIONS)


@app.route("/cities/<region>")
def get_cities(region):
    cities = CITY_DATA.get(region, [])
    return jsonify(cities)


@app.route("/advice", methods=["POST"])
def advice():
    data = request.json or {}
    aqi = data.get("aqi", "unknown")
    region = data.get("region", "not provided")
    city = data.get("city", "not provided")
    household = data.get("household", "general household")
    question = data.get("question", "How should we protect ourselves today?")

    location = f"{city}, {region}" if city and region else (city or region or "not provided")

    user_prompt = (
        f"Location: {location}\n"
        f"Current AQI: {aqi}\n"
        f"Household situation: {household}\n"
        f"User question: {question}"
    )

    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.5,
            max_tokens=500,
        )
        reply = completion.choices[0].message.content
        return jsonify({"ok": True, "advice": reply})
    except Exception as e:
        return jsonify({
            "ok": False,
            "advice": "Sorry, AirBuddy cannot reach the air assistant right now. Please try again later.",
            "error": str(e),
        }), 500


@app.route("/quota")
def quota():
    try:
        resp = requests.get(
            "https://openrouter.ai/api/v1/key",
            headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"},
            timeout=10,
        )
        data = resp.json()
        return jsonify({
            "ok": True,
            "free_model_daily_requests": data.get("data", {}).get("free_model_daily_requests"),
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/favicon.ico")
def favicon():
    return "", 204


# Local development only. Vercel ignores this block.
if __name__ == "__main__":
    app.run(debug=True)