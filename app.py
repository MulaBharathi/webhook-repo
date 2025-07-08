from flask import Flask, request, render_template, jsonify
from pymongo import MongoClient
from datetime import datetime, timezone
import os
from dotenv import load_dotenv
import traceback

# Load environment variables from .env
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
    """Safely parse ISO timestamps to datetime, fallback to now UTC"""
    try:
        return datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)

@app.route('/')
def index():
    latest_event = collection.find_one(sort=[('_id', -1)])
    # Convert timestamp string to datetime if needed
    if latest_event and 'timestamp' in latest_event:
        ts = latest_event['timestamp']
        if isinstance(ts, str):
            latest_event['timestamp'] = parse_timestamp(ts)
    return render_template('index.html', data=latest_event)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        print("=== Headers ===")
        print(dict(request.headers))

        raw_body = request.data.decode("utf-8")
        print("=== Raw body ===")
        print(raw_body)

        payload = request.get_json(force=True)
        if not payload:
            return jsonify({"message": "Empty payload"}), 400

        action = None
        author = None
        from_branch = None
        to_branch = None
        timestamp = datetime.now(timezone.utc)

        # Handle push event
        if 'pusher' in payload and 'ref' in payload and 'head_commit' in payload:
            action = "push"
            author = payload['pusher'].get('name', 'unknown')
            to_branch = payload['ref'].split('/')[-1]
            timestamp = parse_timestamp(payload['head_commit'].get('timestamp', ''))

        # Handle pull request opened event
        elif payload.get("action") == "opened" and "pull_request" in payload:
            action = "pull_request"
            pr = payload["pull_request"]
            author = pr["user"].get("login", "unknown")
            from_branch = pr["head"].get("ref", None)
            to_branch = pr["base"].get("ref", None)
            timestamp = parse_timestamp(pr.get("created_at", ''))

        # Handle pull request merged event
        elif payload.get("action") == "closed" and payload.get("pull_request", {}).get("merged"):
            action = "merge"
            pr = payload["pull_request"]
            author = pr["user"].get("login", "unknown")
            from_branch = pr["head"].get("ref", None)
            to_branch = pr["base"].get("ref", None)
            timestamp = parse_timestamp(pr.get("merged_at", ''))

        if not action:
            print("[WARN] Unrecognized event")
            return jsonify({"message": "Event ignored"}), 400

        # Store in MongoDB
        doc = {
            "action": action,
            "author": author,
            "from_branch": from_branch,
            "to_branch": to_branch,
            "timestamp": timestamp.isoformat(),
            "received_at": datetime.now(timezone.utc).isoformat()
        }
        collection.insert_one(doc)
        print(f"[INFO] Stored {action} event by {author}")
        return jsonify({"message": "Event stored"}), 200

    except Exception as e:
        print("[ERROR] Processing error:", e)
        traceback.print_exc()
        return jsonify({"message": "Server error"}), 500

if __name__ == '__main__':
    app.run(debug=True)

