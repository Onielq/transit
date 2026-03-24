#!/usr/bin/env python3
"""
Plateau Transit — GTFS-RT Simulator
Serves GTFS Realtime feeds on port 5000:
  GET /vehicle_positions  → FeedMessage (JSON)
  GET /trip_updates       → FeedMessage (JSON)
  GET /service_alerts     → FeedMessage (JSON)

When RURA provides a real GPS feed, replace the simulate_* functions
with actual data pulls from the operator API or your crowdsourced DB.

Install: pip install flask requests
Run:     python3 gtfs_rt_simulator.py
"""

import json, math, random, time
from datetime import datetime, timezone
from flask import Flask, jsonify, Response

app = Flask(__name__)

# ─── Static route data (mirrors the GTFS feed) ────────────────────────
ROUTES = [
    {"id": "101", "stops": ["s3","s2"],          "name": "Remera–Downtown"},
    {"id": "102", "stops": ["s19","s3","s1"],     "name": "Kabuga–Nyabugogo"},
    {"id": "105", "stops": ["s3","s7","s1"],      "name": "Remera–Nyabugogo (Kacyiru)"},
    {"id": "106", "stops": ["s3","s9"],           "name": "Remera–Ndera"},
    {"id": "114", "stops": ["s3","s6"],           "name": "Remera–Kanombe–Kibaya"},
    {"id": "202", "stops": ["s5","s2"],           "name": "Nyanza–Downtown"},
    {"id": "212", "stops": ["s1","s16","s8"],     "name": "Nyabugogo–Saint Joseph"},
    {"id": "301", "stops": ["s2","s14"],          "name": "Downtown–Kinyinya"},
    {"id": "302", "stops": ["s4","s3","s2"],      "name": "Kimironko–Downtown"},
    {"id": "305", "stops": ["s1","s7","s4"],      "name": "Nyabugogo–Kimironko"},
    {"id": "401", "stops": ["s2","s16"],          "name": "Downtown–Nyamirambo"},
    {"id": "415", "stops": ["s1","s2"],           "name": "Nyabugogo–Downtown"},
]

STOP_COORDS = {
    "s1":  {"lat": -1.9441, "lon": 30.0619},
    "s2":  {"lat": -1.9536, "lon": 30.0606},
    "s3":  {"lat": -1.9494, "lon": 30.1098},
    "s4":  {"lat": -1.9255, "lon": 30.1177},
    "s5":  {"lat": -2.3545, "lon": 29.7395},
    "s6":  {"lat": -1.9750, "lon": 30.1580},
    "s7":  {"lat": -1.9350, "lon": 30.0800},
    "s8":  {"lat": -1.9680, "lon": 30.0400},
    "s9":  {"lat": -1.9380, "lon": 30.1510},
    "s14": {"lat": -1.9150, "lon": 30.1080},
    "s16": {"lat": -1.9650, "lon": 30.0550},
    "s19": {"lat": -1.9440, "lon": 30.1250},
}

# ─── In-memory vehicle state ──────────────────────────────────────────
_vehicles = {}

def init_vehicles():
    for route in ROUTES:
        for i in range(2):    # 2 buses per route
            vid = f"{route['id']}_B{i+1}"
            stops = route["stops"]
            stop_idx = i % len(stops)
            _vehicles[vid] = {
                "vehicle_id":   vid,
                "route_id":     route["id"],
                "route_name":   route["name"],
                "stop_ids":     stops,
                "stop_idx":     stop_idx,
                "lat":          STOP_COORDS.get(stops[stop_idx], {}).get("lat", -1.9441),
                "lon":          STOP_COORDS.get(stops[stop_idx], {}).get("lon", 30.0619),
                "bearing":      random.uniform(0, 360),
                "speed":        random.uniform(15, 35),
                "occupancy":    random.choice(["EMPTY","MANY_SEATS_AVAILABLE","STANDING_ROOM_ONLY"]),
                "status":       random.choice(["ON_TIME","ON_TIME","ON_TIME","DELAYED"]),
                "next_stop_eta": random.randint(60, 600),   # seconds
                "timestamp":    int(time.time()),
            }

init_vehicles()

def tick_vehicles():
    """Advance vehicle positions. Call on each request for simulation."""
    now = int(time.time())
    for vid, v in _vehicles.items():
        elapsed = now - v["timestamp"]
        stops = v["stop_ids"]
        # Every 90s simulate bus moving to next stop
        if elapsed > 90:
            v["stop_idx"] = (v["stop_idx"] + 1) % len(stops)
            sid = stops[v["stop_idx"]]
            c = STOP_COORDS.get(sid, {"lat": v["lat"], "lon": v["lon"]})
            # Add small GPS jitter (±0.0005°) to simulate GPS noise
            v["lat"] = c["lat"] + random.uniform(-0.0005, 0.0005)
            v["lon"] = c["lon"] + random.uniform(-0.0005, 0.0005)
            v["bearing"] = random.uniform(0, 360)
            v["speed"] = random.uniform(10, 40)
            v["next_stop_eta"] = random.randint(60, 480)
            v["occupancy"] = random.choice(["EMPTY","MANY_SEATS_AVAILABLE",
                                             "MANY_SEATS_AVAILABLE","STANDING_ROOM_ONLY"])
            v["status"] = random.choice(["ON_TIME","ON_TIME","ON_TIME","ON_TIME","DELAYED","SKIPPED"])
            v["timestamp"] = now

# ─── GTFS-RT style JSON (simplified — not protobuf) ───────────────────
def make_feed_header(entity_type):
    return {
        "gtfs_realtime_version": "2.0",
        "incrementality": "FULL_DATASET",
        "timestamp": int(time.time()),
        "entity_type": entity_type,
    }

@app.route("/vehicle_positions")
def vehicle_positions():
    tick_vehicles()
    entities = []
    for vid, v in _vehicles.items():
        entities.append({
            "id": vid,
            "vehicle": {
                "trip": {
                    "trip_id":   f"LIVE_{v['route_id']}",
                    "route_id":  v["route_id"],
                    "direction_id": 0,
                },
                "vehicle": {
                    "id":    vid,
                    "label": f"Bus {v['route_id']}-{vid[-2:]}",
                },
                "position": {
                    "latitude":  round(v["lat"], 6),
                    "longitude": round(v["lon"], 6),
                    "bearing":   round(v["bearing"], 1),
                    "speed":     round(v["speed"] / 3.6, 2),   # m/s
                },
                "current_stop_sequence": v["stop_idx"] + 1,
                "current_status":        "IN_TRANSIT_TO",
                "timestamp":             v["timestamp"],
                "occupancy_status":      v["occupancy"],
                "congestion_level":      "RUNNING_SMOOTHLY",
            }
        })
    return jsonify({"header": make_feed_header("VehiclePosition"), "entity": entities})

@app.route("/trip_updates")
def trip_updates():
    tick_vehicles()
    entities = []
    for vid, v in _vehicles.items():
        stops = v["stop_ids"]
        next_idx = (v["stop_idx"] + 1) % len(stops)
        next_sid = stops[next_idx]

        delay = 0 if v["status"] == "ON_TIME" else random.randint(120, 600)

        entities.append({
            "id": f"TU_{vid}",
            "trip_update": {
                "trip": {
                    "trip_id":   f"LIVE_{v['route_id']}",
                    "route_id":  v["route_id"],
                    "direction_id": 0,
                },
                "vehicle": {"id": vid},
                "stop_time_update": [
                    {
                        "stop_sequence":   next_idx + 1,
                        "stop_id":         next_sid,
                        "arrival":  {"delay": delay, "time": int(time.time()) + v["next_stop_eta"] + delay},
                        "departure":{"delay": delay, "time": int(time.time()) + v["next_stop_eta"] + delay + 30},
                    }
                ],
                "timestamp": v["timestamp"],
                "delay":     delay,
            }
        })
    return jsonify({"header": make_feed_header("TripUpdate"), "entity": entities})

@app.route("/service_alerts")
def service_alerts():
    # Static sample alerts — in production, pull from crowd_reports table
    alerts = [
        {
            "id": "ALT_001",
            "alert": {
                "active_period": [{"start": int(time.time()), "end": int(time.time()) + 3600}],
                "informed_entity": [{"route_id": "202"}, {"route_id": "203"}],
                "cause": "TRAFFIC",
                "effect": "MODIFIED_SERVICE",
                "header_text": {"translation": [{"text": "Route 202/203 — Possible delay near Gikondo", "language": "en"}]},
                "description_text": {"translation": [{"text": "Road works on KN 5 Rd near Gikondo market. Allow extra 10–15 minutes.", "language": "en"}]},
                "severity_level": "WARNING",
            }
        }
    ]
    return jsonify({"header": make_feed_header("Alert"), "entity": alerts})

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "mode": "simulation",  # Change to "live" when real GPS is connected
        "vehicles": len(_vehicles),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "note": "Replace simulate_* with real RURA GPS data when available"
    })

@app.route("/")
def index():
    return jsonify({
        "service": "Plateau Transit GTFS-RT",
        "version": "2.0",
        "endpoints": {
            "vehicle_positions": "/vehicle_positions",
            "trip_updates":      "/trip_updates",
            "service_alerts":    "/service_alerts",
            "health":            "/health",
        },
        "format": "GTFS-RT 2.0 (JSON — upgrade to protobuf for Google Maps submission)",
        "docs":   "https://developers.google.com/transit/gtfs-realtime/reference"
    })

if __name__ == "__main__":
    print("Plateau Transit GTFS-RT Simulator")
    print(f"  Vehicles simulated: {len(_vehicles)}")
    print("  http://localhost:5000/vehicle_positions")
    print("  http://localhost:5000/trip_updates")
    print("  http://localhost:5000/service_alerts\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
