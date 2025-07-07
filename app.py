from flask import Flask, request, render_template
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv
import traceback
load_dotenv()

app = Flask(__name__)

# MongoDB setup
client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB")]
collection = db[os.getenv("MONGO_COLLECTION")]

@app.route('/')
def index():
    latest = collection.find_one(sort=[("timestamp", -1)])
    
    if latest and isinstance(latest["timestamp"], str):
        latest["timestamp"] = datetime.strptime(latest["timestamp"], "%Y-%m-%dT%H:%M:%SZ")

    return render_template("index.html", data=latest)

@app.route('/webhook', methods=['POST'])
def webhook():
    payload = request.json
    action_type = None
    author = None
    from_branch = None
    to_branch = None
    timestamp = datetime.utcnow()

    try:
        # Push event
        if 'pusher' in payload:
            action_type = "push"
            author = payload['pusher'].get('name', 'unknown')
            to_branch = payload.get('ref', '').split('/')[-1]
            head_commit = payload.get('head_commit')
            if head_commit and 'timestamp' in head_commit:
                timestamp = datetime.strptime(payload['head_commit']['timestamp'], "%Y-%m-%dT%H:%M:%SZ")
            else:
                timestamp = datetime.utcnow()  # fallback

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
            print(f"[INFO] Storing document: {doc}")  # Log for debugging
            collection.insert_one(doc)
            return {"message": "Event stored"}, 200

        return {"message": "Unhandled event"}, 400

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return {"message": "Server error", "error": str(e)}, 500

if __name__ == '__main__':
    app.run(debug=True)

