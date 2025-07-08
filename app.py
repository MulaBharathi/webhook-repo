from flask import Flask, request, render_template, jsonify
from pymongo import MongoClient
from datetime import datetime, timezone
import os
from dotenv import load_dotenv
import traceback

# Load environment variables
load_dotenv()

app = Flask(__name__)

# MongoDB setup
mongo_uri = os.getenv("MONGO_URI")
mongo_db = os.getenv("MONGO_DB")
mongo_collection = os.getenv("MONGO_COLLECTION")

client = MongoClient(mongo_uri)
db = client[mongo_db]
collection = db[mongo_collection]


def parse_timestamp(ts_str):
    try:
        return datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


@app.route('/')
def index():
    latest_event = collection.find_one(sort=[('timestamp', -1)])
    if latest_event and isinstance(latest_event.get('timestamp'), str):
        latest_event['timestamp'] = parse_timestamp(latest_event['timestamp'])
    return render_template('index.html', data=latest_event)


@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        print("\n=== Incoming Webhook ===")
        print("Headers:", dict(request.headers))
        raw_body = request.data.decode("utf-8")
        print("Raw body:", raw_body)

        payload = request.get_json(force=True, silent=True)
        if not payload:
            print("[ERROR] Empty or invalid payload")
            return jsonify({"message": "Invalid JSON"}), 400

        event_type = request.headers.get("X-GitHub-Event", "unknown")
        print(f"GitHub Event Type: {event_type}")
        print(f"Payload action: {payload.get('action')}")

        action = None
        author = None
        from_branch = None
        to_branch = None
        timestamp = datetime.now(timezone.utc)

        # Handle push
        if event_type == "push":
            action = "push"
            author = payload['pusher'].get('name', 'unknown')
            to_branch = payload['ref'].split('/')[-1]
            timestamp = parse_timestamp(payload['head_commit'].get('timestamp', ''))

        # Handle pull request opened
        elif event_type == "pull_request" and payload.get("action") == "opened":
            action = "pull_request"
            pr = payload["pull_request"]
            author = pr["user"].get("login", "unknown")
            from_branch = pr["head"].get("ref")
            to_branch = pr["base"].get("ref")
            timestamp = parse_timestamp(pr.get("created_at", ''))

        # Handle pull request merged
        elif event_type == "pull_request" and payload.get("action") == "closed" and payload.get("pull_request", {}).get("merged"):
            action = "merge"
            pr = payload["pull_request"]
            author = pr["user"].get("login", "unknown")
            from_branch = pr["head"].get("ref")
            to_branch = pr["base"].get("ref")
            timestamp = parse_timestamp(pr.get("merged_at", ''))

        if not action:
            print("[WARN] Unhandled or irrelevant event.")
            return jsonify({"message": "Event not handled"}), 400

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
        return jsonify({"message": f"{action} event stored"}), 200

    except Exception as e:
        print("[ERROR] Exception occurred:", e)
        traceback.print_exc()
        return jsonify({"message": "Server error"}), 500


if __name__ == '__main__':
    app.run(debug=True)
