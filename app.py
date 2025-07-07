from flask import Flask, request, render_template
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

print(f"[DEBUG] Connecting to MongoDB → URI: {mongo_uri}, DB: {mongo_db}, Collection: {mongo_collection}")

client = MongoClient(mongo_uri)
db = client[mongo_db]
collection = db[mongo_collection]

@app.route('/')
def index():
    latest = collection.find_one(sort=[("timestamp", -1)])
    
    if latest and isinstance(latest.get("timestamp"), str):
        try:
            latest["timestamp"] = datetime.strptime(latest["timestamp"], "%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            try:
                latest["timestamp"] = datetime.fromisoformat(latest["timestamp"])
            except:
                latest["timestamp"] = datetime.now(timezone.utc)

    return render_template("index.html", data=latest)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        payload = request.get_json(force=True)
        print("[DEBUG] Payload received:", payload)

        if 'zen' in payload:
            print("[INFO] Ping event received.")
            return {"message": "Ping received"}, 200

        action_type = None
        author = None
        from_branch = None
        to_branch = None
        timestamp = datetime.now(timezone.utc)

        # Push event
        if 'pusher' in payload:
            action_type = "push"
            author = payload['pusher'].get('name', 'unknown')
            to_branch = payload.get('ref', '').split('/')[-1]
            head_commit = payload.get('head_commit')
            if head_commit and 'timestamp' in head_commit:
                timestamp = datetime.strptime(head_commit['timestamp'], "%Y-%m-%dT%H:%M:%SZ")

        # Pull Request opened
        elif payload.get("action") == "opened" and "pull_request" in payload:
            action_type = "pull_request"
            pr = payload["pull_request"]
            author = pr["user"]["login"]
            from_branch = pr["head"]["ref"]
            to_branch = pr["base"]["ref"]
            timestamp = datetime.strptime(pr["created_at"], "%Y-%m-%dT%H:%M:%SZ")

        # Pull Request merged
        elif payload.get("action") == "closed" and payload.get("pull_request", {}).get("merged"):
            action_type = "merge"
            pr = payload["pull_request"]
            author = pr["user"]["login"]
            from_branch = pr["head"]["ref"]
            to_branch = pr["base"]["ref"]
            timestamp = datetime.strptime(pr["merged_at"], "%Y-%m-%dT%H:%M:%SZ")

        if action_type:
            doc = {
                "action": action_type,
                "author": author,
                "from_branch": from_branch,
                "to_branch": to_branch,
                "timestamp": timestamp
            }
            print(f"[INFO] Storing document: {doc}")
            collection.insert_one(doc)
            return {"message": "Event stored"}, 200

        return {"message": "Unhandled event"}, 400

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        traceback.print_exc()
        return {"message": "Server error", "error": str(e)}, 500

if __name__ == '__main__':
    app.run(debug=True)

