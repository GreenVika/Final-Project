from flask import Flask, request, jsonify, render_template
from flask_pymongo import PyMongo
from flask_cors import CORS
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import os, requests

# Load environment variables
load_dotenv()

app = Flask(
    __name__,
    static_url_path="/static",
    static_folder="static",
    template_folder="templates"
)

# Enable CORS for deployed frontend
CORS(app, supports_credentials=True)

# --- Config ---
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://mood_user:kasamu19@cluster0.tczypxu.mongodb.net/mood_journal?retryWrites=true&w=majority"
)
HF_TOKEN = os.getenv("HF_API_TOKEN", "HF_TOKEN_REMOVED")
HF_MODEL = os.getenv("HF_MODEL", "j-hartmann/emotion-english-distilroberta-base")

if not MONGO_URI:
    raise RuntimeError("MONGO_URI is not set in environment")
if not HF_TOKEN:
    raise RuntimeError("HF_API_TOKEN is not set in environment")

app.config["MONGO_URI"] = MONGO_URI
mongo = PyMongo(app)
entries_col = mongo.db.entries

# Test MongoDB connection
try:
    mongo.cx.admin.command("ping")
    print("✅ MongoDB connection successful!")
except Exception as e:
    print("❌ MongoDB connection failed:", e)


# --- Utilities ---
def analyze_emotions(text: str):
    url = f"https://router.huggingface.co/hf-inference/models/{HF_MODEL}"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    resp = requests.post(url, headers=headers, json={"inputs": text}, timeout=30)
    resp.raise_for_status()
    payload = resp.json()

    # Normalize payload
    if isinstance(payload, list) and len(payload) > 0 and isinstance(payload[0], list):
        data = payload[0]
    else:
        data = payload

    emotions = {item["label"].lower(): float(item["score"]) for item in data}
    total = sum(emotions.values())
    if "neutral" not in emotions and total < 1.0:
        emotions["neutral"] = 1.0 - total

    emotions_pct = {k: round(v * 100.0, 2) for k, v in emotions.items()}
    top_label = max(emotions_pct, key=emotions_pct.get)
    top_score = emotions_pct[top_label]
    return emotions_pct, top_label, top_score


def start_of_day(dt: datetime):
    return datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc)


# --- Routes ---
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/entries", methods=["POST"])
def create_entry():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Text is required"}), 400

    # Emotion analysis
    try:
        emotions, top_label, top_score = analyze_emotions(text)
    except requests.HTTPError as e:
        return jsonify({"error": f"Hugging Face error: {e.response.text[:200]}"}), 502
    except Exception as e:
        return jsonify({"error": f"Analysis failed: {e}"}), 500

    entry_doc = {
        "text": text,
        "emotions": emotions,
        "top_label": top_label,
        "top_score": top_score,
        "created_at": datetime.now(timezone.utc)
    }

    # Insert into MongoDB
    result = entries_col.insert_one(entry_doc)
    entry_doc["_id"] = str(result.inserted_id)
    entry_doc["created_at"] = entry_doc["created_at"].isoformat()

    return jsonify(entry_doc), 201


@app.route("/api/entries", methods=["GET"])
def list_entries():
    days = int(request.args.get("days", 30))
    since = datetime.now(timezone.utc) - timedelta(days=days)
    entries = list(entries_col.find({"created_at": {"$gte": since}}).sort("created_at", 1))

    for e in entries:
        e["id"] = str(e.pop("_id"))
        e["created_at"] = e["created_at"].isoformat()
    return jsonify(entries)


@app.route("/api/stats", methods=["GET"])
def stats():
    days = int(request.args.get("days", 30))
    since = start_of_day(datetime.now(timezone.utc) - timedelta(days=days))
    entries = list(entries_col.find({"created_at": {"$gte": since}}).sort("created_at", 1))

    buckets = {}
    for e in entries:
        day = start_of_day(e["created_at"]).date().isoformat()
        if day not in buckets:
            buckets[day] = {"count": 0, "emotions": {}}
        buckets[day]["count"] += 1
        for k, v in e["emotions"].items():
            buckets[day]["emotions"][k] = buckets[day]["emotions"].get(k, 0) + v

    series = []
    all_labels = set()
    for day, info in sorted(buckets.items()):
        avg = {k: round(v / info["count"], 2) for k, v in info["emotions"].items()}
        all_labels.update(avg.keys())
        series.append({"date": day, **avg})

    return jsonify({"labels": sorted(all_labels), "series": series})


@app.route("/api/insights", methods=["GET"])
def insights():
    today = start_of_day(datetime.now(timezone.utc))
    week_1_start = today - timedelta(days=7)
    week_2_start = today - timedelta(days=14)

    week1 = list(entries_col.find({"created_at": {"$gte": week_1_start}}))
    week2 = list(entries_col.find({"created_at": {"$gte": week_2_start, "$lt": week_1_start}}))

    def avg_emotions(entries):
        sums = {}
        if not entries:
            return {}
        for e in entries:
            for k, v in e["emotions"].items():
                sums[k] = sums.get(k, 0) + v
        return {k: round(sums[k] / len(entries), 2) for k in sums}

    a1, a2 = avg_emotions(week1), avg_emotions(week2)

    all_keys = set(a1.keys()) | set(a2.keys())
    diffs = []
    for k in all_keys:
        v1, v2 = a1.get(k, 0.0), a2.get(k, 0.0)
        delta = round(v1 - v2, 2)
        if abs(delta) >= 1.0:
            direction = "up" if delta > 0 else "down"
            diffs.append({"emotion": k, "delta": delta, "direction": direction})

    summary = []
    if diffs:
        ups = [d for d in diffs if d["direction"] == "up"]
        downs = [d for d in diffs if d["direction"] == "down"]
        if ups:
            winner = max(ups, key=lambda d: abs(d["delta"]))
            summary.append(
                f"You’ve been experiencing more {winner['emotion']} this week (+{winner['delta']} pts) compared to last week."
            )
        if downs:
            drop = max(downs, key=lambda d: abs(d["delta"]))
            summary.append(
                f"{drop['emotion'].capitalize()} decreased this week ({drop['delta']} pts). Keep noting what helped."
            )
    else:
        summary.append("Your mood levels are stable week over week. Nice consistency!")

    top_this_week = sorted(a1.items(), key=lambda kv: kv[1], reverse=True)[:3]
    top_str = ", ".join([f"{k} ({v})" for k, v in top_this_week]) if top_this_week else "No data yet."
    summary.append(f"Top emotions this week: {top_str}")

    return jsonify({"week_this": a1, "week_last": a2, "changes": diffs, "summary": summary})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
