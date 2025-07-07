from flask import Flask, request, render_template
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# MongoDB setup
client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB")]
collection = db[os.getenv("MONGO_COLLECTION")]

@app.route('/')
def index():
    latest = collection.find_one(sort=[("timestamp", -1)])
    return render_template("index.html", data=latest)

@app.route('/webhook', methods=['POST'])
def webhook():
    payload = request.json
    action_type = None
    author = None
    from_branch = None
    to_branch = None
    timestamp = datetime.utcnow()

    # Push event
    if 'pusher' in payload:
        action_type = "push"
        author = payload['pusher']['name']
        to_branch = payload['ref'].split('/')[-1]
        timestamp = datetime.strptime(payload('head_commit['timestamp'], "%Y-%m-%dT%H:%M:%SZ")

    # Pull Request event
    elif payload.get("action") == "opened" and "pull_request" in payload:
        action_type = "pull_request"
        pr = payload["pull_request"]
        author = pr["user"]["login"]
        from_branch = pr["head"]["ref"]
        to_branch = pr["base"]["ref"]
        timestamp = datetime.strptime(pr["created_at"], "%Y-%m-%dT%H:%M:%SZ")

    # Merge event (pull_request closed with merged = true)
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

if __name__ == '__main__':
    app.run(debug=True)

