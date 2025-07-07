from flask import Flask, request, render_template
from pymongo import MongoClient
from datetime import datetime, timezone
import os
from dotenv import load_dotenv
import traceback

# Load env variables
load_dotenv()

app = Flask(__name__)

# MongoDB connection
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
        try:
            latest["timestamp"] = datetime.strptime(latest["timestamp"], "%Y-%m-%dT%H:%M:%SZ")
        except:
            latest["timestamp"] = datetime.now(timezone.utc)

    return render_template("index.html", data=latest)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        payload = request.get_json(force=True)
        print("[DEBUG] Payload received:", payload)

        if 'zen' in payload:
            return {"message": "Ping received"}, 200

        action_type = None
        author = None
        from_branch = None
        to_branch = None
        timestamp = datetime.now(timezone.utc)

        if 'pusher' in payload:
            action_type = "push"
            author = payload['pusher'].get('name', 'unknown')
            to_branch = payload.get('ref', '').split('/')[-1]
            if 'head_commit' in payload and payload['head_commit']:
                timestamp = datetime.strptime(payload['head_commit']['timestamp'], "%Y-%m-%dT%H:%M:%SZ")

        elif payload.get("action") == "opened" and "pull_request" in payload:
            action_type = "pull_request"
            pr = payload["pull_request"]
            author = pr["user"]["login"]
            from_branch = pr["head"]["ref"]
            to_branch = pr["base"]["ref"]
            timestamp = datetime.strptime(pr["created_at"], "%Y-%m-%dT%H:%M:%SZ")

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
            collection.insert_one(doc)
            return {"message": "Event stored"}, 200

        return {"message": "Unhandled event"}, 400

    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}, 500

if __name__ == '__main__':
    app.run(debug=True)


