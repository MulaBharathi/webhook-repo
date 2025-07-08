from flask import Flask, request, render_template, jsonify
from pymongo import MongoClient
from datetime import datetime, timezone
import os
from dotenv import load_dotenv
import traceback

# Load environment variables
load_dotenv()

app = Flask(__name__)

# MongoDB connection setup
mongo_uri = os.getenv("MONGO_URI")
mongo_db = os.getenv("MONGO_DB")
mongo_collection = os.getenv("MONGO_COLLECTION")

client = MongoClient(mongo_uri)
db = client[mongo_db]
collection = db[mongo_collection]

def parse_timestamp(timestamp_str):
    try:
        # Try parsing with microseconds and timezone offset first
        return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    except Exception:
        # Fallback: current UTC time
        return datetime.now(timezone.utc)


# Custom Jinja filter for ordinal suffix
def ordinal_suffix(value):
    n = int(value)
    if 11 <= (n % 100) <= 13:
        return "th"
    else:
        return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")

app.jinja_env.filters['ordinal_suffix'] = ordinal_suffix

@app.route('/')
def index():
    latest_event = collection.find_one(sort=[('_id', -1)])
    if latest_event and 'timestamp' in latest_event:
        ts = latest_event['timestamp']
        if isinstance(ts, str):
            latest_event['timestamp'] = parse_timestamp(ts)
    return render_template('index.html', data=latest_event)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        payload = request.get_json(force=True)
        if not payload:
            return jsonify({"message": "Empty payload"}), 400

        action = None
        author = None
        from_branch = None
        to_branch = None
        timestamp = datetime.now(timezone.utc)

        # PUSH event
        if 'pusher' in payload and 'ref' in payload and 'head_commit' in payload:
            action = "push"
            author = payload['pusher'].get('name', 'unknown')
            to_branch = payload['ref'].split('/')[-1]
            timestamp = parse_timestamp(payload['head_commit'].get('timestamp', ''))

        # PULL_REQUEST opened
        elif payload.get("action") == "opened" and "pull_request" in payload:
            action = "pull_request"
            pr = payload["pull_request"]
            author = pr["user"].get("login", "unknown")
            from_branch = pr["head"].get("ref", None)
            to_branch = pr["base"].get("ref", None)
            timestamp = parse_timestamp(pr.get("created_at", ''))

        # PULL_REQUEST merged (closed and merged)
        elif payload.get("action") == "closed" and payload.get("pull_request", {}).get("merged"):
            action = "merge"
            pr = payload["pull_request"]
            author = pr["user"].get("login", "unknown")
            from_branch = pr["head"].get("ref", None)
            to_branch = pr["base"].get("ref", None)
            timestamp = parse_timestamp(pr.get("merged_at", ''))

        if not action:
            return jsonify({"message": "Event ignored"}), 400

        # Save to MongoDB with ISO format timestamp strings
        doc = {
            "action": action,
            "author": author,
            "from_branch": from_branch,
            "to_branch": to_branch,
            "timestamp": timestamp.isoformat(),
            "received_at": datetime.now(timezone.utc).isoformat()
        }
        collection.insert_one(doc)
        print(f"[INFO] Stored event: {action} by {author}")
        return jsonify({"message": "Event stored"}), 200

    except Exception as e:
        print("[ERROR] Exception while processing webhook:")
        traceback.print_exc()
        return jsonify({"message": "Server error"}), 500

if __name__ == '__main__':
    app.run(debug=True)
