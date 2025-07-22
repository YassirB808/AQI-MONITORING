from flask import Flask, render_template, jsonify
import threading
import time
import requests

app = Flask(__name__)

locations = [
    {"name": "Beijing", "lat": 39.9042, "lon": 116.4074},
    {"name": "Shanghai", "lat": 31.2304, "lon": 121.4737},
    {"name": "Guangzhou", "lat": 23.1291, "lon": 113.2644},
    {"name": "Shenzhen", "lat": 22.5431, "lon": 114.0579},
    {"name": "Rabat", "lat": 34.020882, "lon": -6.841650},
    {"name": "Casablanca", "lat": 33.5731, "lon": -7.5898},
    {"name": "Marrakesh", "lat": 31.6300, "lon": -7.9890},
    {"name": "Ifrane", "lat": 33.5333, "lon": -5.1167},
    {"name": "Tanger", "lat": 35.7595, "lon": -5.8339},
]

gcp_api_key = "yourkey"
ubidots_token = "yourtoken"
device_label = "air_quality_monitor"

# Shared data store for AQI results
aqi_data = {}

def get_aqi(lat, lon):
    url = f"https://airquality.googleapis.com/v1/currentConditions:lookup?key={gcp_api_key}"
    payload = {"location": {"latitude": lat, "longitude": lon}}
    try:
        res = requests.post(url, json=payload, timeout=10)
        res.raise_for_status()
        data = res.json()
        aqi = data['indexes'][0]['aqi']
        category = data['indexes'][0]['category']
        return aqi, category
    except Exception as e:
        print(f"[{time.ctime()}] Failed to get AQI for ({lat}, {lon}): {e}")
        return None, None

def send_to_ubidots(city, value, category):
    if value is None or category is None:
        print(f"Skipped {city} due to missing AQI value or category.")
        return
    url = f"https://industrial.api.ubidots.com/api/v1.6/devices/{device_label}/"
    headers = {
        "X-Auth-Token": ubidots_token,
        "Content-Type": "application/json"
    }
    payload = {
        f"aqi_{city.lower()}": {
            "value": value,
            "context": {"category": category}
        }
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        print(f"[{time.ctime()}] Sent {city} AQI to Ubidots: {res.status_code}")
    except Exception as e:
        print(f"Failed to send {city} data to Ubidots: {e}")

def fetch_aqi_periodically():
    while True:
        for loc in locations:
            aqi, category = get_aqi(loc["lat"], loc["lon"])
            aqi_data[loc["name"]] = {"aqi": aqi, "category": category, "last_update": time.ctime()}
            send_to_ubidots(loc["name"], aqi, category)
            time.sleep(5)  # small delay between cities
        time.sleep(600)  # 10 minutes delay before next update

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/aqi')
def api_aqi():
    return jsonify(aqi_data)

if __name__ == '__main__':
    # Start background thread to fetch AQI
    threading.Thread(target=fetch_aqi_periodically, daemon=True).start()
    app.run(debug=True)
