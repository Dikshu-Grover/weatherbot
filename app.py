import os
import requests
import cohere

from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

# ----------------------------
# Load Environment Variables
# ----------------------------

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "weathergpt")

# ----------------------------
# Cohere API
# ----------------------------

COHERE_API_KEY = os.getenv("COHERE_API_KEY")

if not COHERE_API_KEY:
    raise Exception("COHERE_API_KEY not found in .env")

co = cohere.ClientV2(api_key=COHERE_API_KEY)


# ----------------------------
# Weather Code Mapping
# ----------------------------

def weather_description(code):
    weather_codes = {
        0: "Clear Sky",
        1: "Mainly Clear",
        2: "Partly Cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Fog",
        51: "Light Drizzle",
        53: "Moderate Drizzle",
        55: "Heavy Drizzle",
        56: "Freezing Drizzle",
        57: "Heavy Freezing Drizzle",
        61: "Light Rain",
        63: "Moderate Rain",
        65: "Heavy Rain",
        66: "Freezing Rain",
        67: "Heavy Freezing Rain",
        71: "Light Snow",
        73: "Moderate Snow",
        75: "Heavy Snow",
        77: "Snow Grains",
        80: "Rain Showers",
        81: "Heavy Rain Showers",
        82: "Violent Rain Showers",
        85: "Snow Showers",
        86: "Heavy Snow Showers",
        95: "Thunderstorm",
        96: "Thunderstorm with Hail",
        99: "Severe Thunderstorm with Hail"
    }

    return weather_codes.get(code, "Unknown")


# ----------------------------
# Routes
# ----------------------------

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/ask", methods=["POST"])
def ask():

    try:
        data = request.get_json()

        city = data.get("city", "").strip()
        question = data.get("question", "").strip()

        if city == "":
            return jsonify({
                "reply": "Please enter a city."
            })

        # ----------------------------
        # Get Latitude & Longitude
        # ----------------------------

        geo_url = (
            f"https://geocoding-api.open-meteo.com/v1/search"
            f"?name={city}&count=1"
        )

        geo = requests.get(geo_url, timeout=10).json()

        if "results" not in geo:
            return jsonify({
                "reply": "City not found."
            })

        location = geo["results"][0]

        latitude = location["latitude"]
        longitude = location["longitude"]
        city_name = location["name"]
        country = location.get("country", "")

        # ----------------------------
        # Get Weather
        # ----------------------------

        weather_url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={latitude}"
            f"&longitude={longitude}"
            "&current="
            "temperature_2m,"
            "apparent_temperature,"
            "relative_humidity_2m,"
            "wind_speed_10m,"
            "weather_code"
        )

        weather = requests.get(weather_url, timeout=10).json()

        current = weather["current"]

        temp = current["temperature_2m"]
        feels = current["apparent_temperature"]
        humidity = current["relative_humidity_2m"]
        wind = current["wind_speed_10m"]
        condition = weather_description(current["weather_code"])

        # ----------------------------
        # AI Prompt
        # ----------------------------

        prompt = f"""
You are WeatherGPT, a helpful weather assistant.

Current Weather:

City: {city_name}, {country}
Temperature: {temp}°C
Feels Like: {feels}°C
Humidity: {humidity}%
Wind Speed: {wind} km/h
Condition: {condition}

User Question:
{question}

Instructions:
- Answer naturally.
- Keep the answer between 3 and 6 sentences.
- Give practical recommendations whenever possible.
"""

        response = co.chat(
            model="command-a",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        reply = response.message.content[0].text

        return jsonify({
            "reply": reply,
            "weather": {
                "city": city_name,
                "temperature": temp,
                "humidity": humidity,
                "wind": wind,
                "condition": condition
            }
        })

    except Exception as e:
        print(e)
        return jsonify({
            "reply": str(e)
        }), 500


# ----------------------------
# Run App
# ----------------------------

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
