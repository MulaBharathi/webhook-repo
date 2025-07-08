from flask import Flask, request, render_template
from pymongo import MongoClient
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

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

@app.route('/')
def index():
    latest = collection.find_one(sort=[("timestamp", -1)])
    if latest and isinstance(latest.get("timestamp"), str):
        latest["timestamp"] = datetime.strptime(latest["timestamp"], "%Y-%m-%dT%H:%M:%SZ")
    return render_template("index.html", data=latest)

@app.route('/webhook', methods=['POST'])
def webhook():
    payload = request.get_json()
    print("[DEBUG] Incoming payload:", payload)
    if not payload:
        print("[ERROR] No payload received")
        return jsonify({"message": "Invalid JSON"}), 400

    event = request.headers.get("X-GitHub-Event")
    print(f"[DEBUG] GitHub Event: {event}")

    action = None
    author = None
    from_branch = None
    to_branch = None
    timestamp = datetime.now(timezone.utc)

    # Handle push event
    if 'pusher' in payload:
        action = "push"
        author = payload['pusher']['name']
        to_branch = payload['ref'].split('/')[-1]
        timestamp = datetime.strptime(payload['head_commit']['timestamp'], "%Y-%m-%dT%H:%M:%SZ")

    # Handle pull request opened
    elif payload.get("action") == "opened" and "pull_request" in payload:
        action = "pull_request"
        pr = payload["pull_request"]
        author = pr["user"]["login"]
        from_branch = pr["head"]["ref"]
        to_branch = pr["base"]["ref"]
        timestamp = datetime.strptime(pr["created_at"], "%Y-%m-%dT%H:%M:%SZ")

    # Handle merged pull request
    elif payload.get("action") == "closed" and payload.get("pull_request", {}).get("merged"):
        action = "merge"
        pr = payload["pull_request"]
        author = pr["user"]["login"]
        from_branch = pr["head"]["ref"]
        to_branch = pr["base"]["ref"]
        timestamp = datetime.strptime(pr["merged_at"], "%Y-%m-%dT%H:%M:%SZ")

    if action:
        collection.insert_one({
            "action": action,
            "author": author,
            "from_branch": from_branch,
            "to_branch": to_branch,
            "timestamp": timestamp,
            "received_at": datetime.now(timezone.utc)
        })
        return {"message": "Event stored"}, 200

    return {"message": "Event ignored"}, 400

if __name__ == '__main__':
    app.run(debug=True)

