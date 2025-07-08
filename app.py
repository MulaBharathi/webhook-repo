from flask import Flask, request, render_template, jsonify
from pymongo import MongoClient
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

# Load environment variables
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
    if latest:
        if isinstance(latest.get("timestamp"), str):
            latest["timestamp"] = datetime.strptime(latest["timestamp"], "%Y-%m-%dT%H:%M:%SZ")
        elif isinstance(latest.get("timestamp"), datetime):
            latest["timestamp"] = latest["timestamp"]
    return render_template("index.html", data=latest)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        print("\n========== HEADERS ==========")
        print(dict(request.headers))

        print("\n========== RAW BODY ==========")
        print(request.data.decode("utf-8"))

        # Force parse JSON
        payload = request.get_json(force=True)

        print("\n========== PARSED PAYLOAD ==========")
        print(payload)

        if not payload:
            print("❌ Empty or invalid payload")
            return jsonify({"message": "Empty payload"}), 400

        action = None
        author = None
        from_branch = None
        to_branch = None
        timestamp = datetime.now(timezone.utc)

        # Handle push
        if 'pusher' in payload:
            action = "push"
            author = payload['pusher']['name']
            to_branch = payload['ref'].split('/')[-1]
            timestamp = datetime.strptime(payload['head_commit']['timestamp'], "%Y-%m-%dT%H:%M:%SZ")

        # Handle pull_request opened
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

        # Store in DB
        if action:
            collection.insert_one({
                "action": action,
                "author": author,
                "from_branch": from_branch,
                "to_branch": to_branch,
                "timestamp": timestamp,
                "received_at": datetime.now(timezone.utc)
            })
            print(f"[✅ Stored] {action} event by {author}")
            return jsonify({"message": "Event stored"}), 200
        else:
            print("[⚠] Event not supported or missing fields")
            return jsonify({"message": "Event ignored"}), 400

    except Exception as e:
        print("❌ Exception:", e)
        return jsonify({"message": "Webhook processing error"}), 500

if __name__ == '__main__':
    app.run(debug=True)

