from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.mysql import JSON
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os, requests, math

load_dotenv()

app = Flask(__name__, static_url_path="/static", static_folder="static", template_folder="templates")

# --- Config ---
DB_URL = os.getenv("DATABASE_URL")  # e.g. mysql+pymysql://user:pass@localhost:3306/mood_journal
HF_TOKEN = os.getenv("HF_API_TOKEN")
HF_MODEL = os.getenv("HF_MODEL", "j-hartmann/emotion-english-distilroberta-base")

if not DB_URL:
    raise RuntimeError("DATABASE_URL is not set in environment")
if not HF_TOKEN:
    raise RuntimeError("HF_API_TOKEN is not set in environment")

app.config["SQLALCHEMY_DATABASE_URI"] = DB_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# --- Models ---
class Entry(db.Model):
    __tablename__ = "entries"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    emotions = db.Column(JSON, nullable=False)  # { "joy": 0.41, "sadness": 0.12, ... }
    top_label = db.Column(db.String(64), nullable=False)
    top_score = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

# --- Utilities ---
def analyze_emotions(text: str):
    """
    Calls Hugging Face Inference API for multi-class emotion analysis.
    Returns a tuple: (emotions_dict, top_label, top_score)
    """
    url = f"https://router.huggingface.co/hf-inference/models/{HF_MODEL}"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    resp = requests.post(url, headers=headers, json={"inputs": text}, timeout=30)
    resp.raise_for_status()
    payload = resp.json()

    # Models can return either a list[0] of scores or just a list
    # Normalize into: [{"label": "...", "score": 0.x}, ...]
    if isinstance(payload, list) and len(payload) > 0 and isinstance(payload[0], list):
        data = payload[0]
    else:
        data = payload

    emotions = {item["label"].lower(): float(item["score"]) for item in data}
    # Ensure a 'neutral' dimension exists (some models include it, some don’t)
    if "neutral" not in emotions:
        # crude estimate: distribute leftover to neutral if total<1
        total = sum(emotions.values())
        neutral_guess = max(0.0, 1.0 - total)
        if neutral_guess > 0:
            emotions["neutral"] = neutral_guess

    # Normalize to percentages (0–100) and round
    emotions_pct = {k: round(v * 100.0, 2) for k, v in emotions.items()}
    # Pick top
    top_label = max(emotions_pct, key=emotions_pct.get)
    top_score = emotions_pct[top_label]
    return emotions_pct, top_label, top_score

def start_of_day(dt: datetime):
    return datetime(dt.year, dt.month, dt.day)

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

    try:
        emotions, top_label, top_score = analyze_emotions(text)
    except requests.HTTPError as e:
        return jsonify({"error": f"Hugging Face error: {e.response.text[:200]}"}), 502
    except Exception as e:
        return jsonify({"error": f"Analysis failed: {e}"}), 500

    entry = Entry(text=text, emotions=emotions, top_label=top_label, top_score=top_score)
    db.session.add(entry)
    db.session.commit()

    return jsonify({
        "id": entry.id,
        "text": entry.text,
        "emotions": entry.emotions,
        "top_label": entry.top_label,
        "top_score": entry.top_score,
        "created_at": entry.created_at.isoformat()
    }), 201

@app.route("/api/entries", methods=["GET"])
def list_entries():
    """
    ?days=7|30|90|365 (default 30)
    """
    days = int(request.args.get("days", 30))
    since = datetime.utcnow() - timedelta(days=days)
    entries = (Entry.query
               .filter(Entry.created_at >= since)
               .order_by(Entry.created_at.asc())
               .all())

    return jsonify([{
        "id": e.id,
        "text": e.text,
        "emotions": e.emotions,
        "top_label": e.top_label,
        "top_score": e.top_score,
        "created_at": e.created_at.isoformat()
    } for e in entries])

@app.route("/api/stats", methods=["GET"])
def stats():
    """
    Returns daily aggregated emotion averages for charting.
    ?days=30
    """
    days = int(request.args.get("days", 30))
    since = start_of_day(datetime.utcnow() - timedelta(days=days))
    entries = (Entry.query
               .filter(Entry.created_at >= since)
               .order_by(Entry.created_at.asc())
               .all())

    # group by day
    buckets = {}
    for e in entries:
        day = start_of_day(e.created_at).date().isoformat()
        if day not in buckets:
            buckets[day] = {"count": 0, "emotions": {}}
        buckets[day]["count"] += 1
        for k, v in e.emotions.items():
            buckets[day]["emotions"][k] = buckets[day]["emotions"].get(k, 0) + v

    # average
    series = []
    all_labels = set()
    for day, info in sorted(buckets.items()):
        avg = {k: round(v / info["count"], 2) for k, v in info["emotions"].items()}
        all_labels.update(avg.keys())
        series.append({"date": day, **avg})

    return jsonify({"labels": sorted(all_labels), "series": series})

@app.route("/api/insights", methods=["GET"])
def insights():
    """
    Compares last 7 days vs the previous 7 days, highlights changes.
    """
    today = start_of_day(datetime.utcnow())
    week_1_start = today - timedelta(days=7)
    week_2_start = today - timedelta(days=14)

    week1 = Entry.query.filter(Entry.created_at >= week_1_start).all()
    week2 = Entry.query.filter(Entry.created_at >= week_2_start, Entry.created_at < week_1_start).all()

    def avg_emotions(entries):
        sums = {}
        if not entries:
            return {}
        for e in entries:
            for k, v in e.emotions.items():
                sums[k] = sums.get(k, 0) + v
        return {k: round(sums[k] / len(entries), 2) for k in sums}

    a1, a2 = avg_emotions(week1), avg_emotions(week2)

    # Compute diffs
    all_keys = set(a1.keys()) | set(a2.keys())
    diffs = []
    for k in all_keys:
        v1, v2 = a1.get(k, 0.0), a2.get(k, 0.0)
        delta = round(v1 - v2, 2)
        if abs(delta) >= 1.0:  # only meaningful changes
            direction = "up" if delta > 0 else "down"
            diffs.append({"emotion": k, "delta": delta, "direction": direction})

    summary = []
    # Friendly sentence or two:
    if diffs:
        ups = [d for d in diffs if d["direction"] == "up"]
        downs = [d for d in diffs if d["direction"] == "down"]
        if ups:
            winner = max(ups, key=lambda d: abs(d["delta"]))
            summary.append(f"You’ve been experiencing more {winner['emotion']} this week (+{winner['delta']} pts) compared to last week.")
        if downs:
            drop = max(downs, key=lambda d: abs(d["delta"]))
            summary.append(f"{drop['emotion'].capitalize()} decreased this week ({drop['delta']} pts). Keep noting what helped.")
    else:
        summary.append("Your mood levels are stable week over week. Nice consistency!")

    # Top emotions this week
    top_this_week = sorted(a1.items(), key=lambda kv: kv[1], reverse=True)[:3]
    top_str = ", ".join([f"{k} ({v})" for k, v in top_this_week]) if top_this_week else "No data yet."
    summary.append(f"Top emotions this week: {top_str}")

    return jsonify({
        "week_this": a1,
        "week_last": a2,
        "changes": diffs,
        "summary": summary
    })

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)
