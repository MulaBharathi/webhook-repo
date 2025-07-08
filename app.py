from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# MongoDB config
client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB")]
collection = db[os.getenv("MONGO_COLLECTION")]

@app.route('/')
def index():
    latest_event = collection.find_one(sort=[('_id', -1)])
    return render_template('index.html', data=latest_event)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        payload = request.get_json(force=True)
        if not payload:
            return "Invalid JSON", 400

        event_type = request.headers.get('X-GitHub-Event', 'unknown')
        action = payload.get("action")

        doc = {
            "event": event_type,
            "received_at": datetime.utcnow(),
        }

        # Handle push events
        if event_type == 'push':
            doc["action"] = "push"
            doc["author"] = payload.get("head_commit", {}).get("author", {}).get("name")
            doc["to_branch"] = payload.get("ref", "").split("/")[-1]

            ts = payload.get("head_commit", {}).get("timestamp")
            if ts:
                try:
                    doc["timestamp"] = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
                except ValueError:
                    doc["timestamp"] = "Invalid timestamp"
            else:
                doc["timestamp"] = "Not available"

        # Handle pull request opened or merged
        elif event_type == 'pull_request':
            pr = payload.get("pull_request", {})
            doc["action"] = action  # could be "opened", "closed", etc.
            doc["author"] = pr.get("user", {}).get("login")
            doc["to_branch"] = pr.get("base", {}).get("ref")

            ts = pr.get("created_at") if action == "opened" else pr.get("merged_at")
            if ts:
                try:
                    doc["timestamp"] = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
                except ValueError:
                    doc["timestamp"] = "Invalid timestamp"
            else:
                doc["timestamp"] = "Not available"

        else:
            doc["note"] = f"Unhandled event: {event_type}"

        collection.insert_one(doc)
        print(f"✅ Saved {event_type} - {action}")
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)

