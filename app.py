from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

# Flask app
app = Flask(__name__)

# MongoDB connection
mongo_uri = os.getenv("MONGO_URI")
mongo_db = os.getenv("MONGO_DB")
mongo_collection = os.getenv("MONGO_COLLECTION")

client = MongoClient(mongo_uri)
db = client[mongo_db]
collection = db[mongo_collection]

# UI route: display latest event (auto-refresh every 15s via index.html)
@app.route("/")
def index():
    latest = collection.find_one(sort=[("timestamp", -1)])
    return render_template("index.html", data=latest)

# Webhook endpoint
@app.route("/webhook", methods=["POST"])
def webhook():
    if not request.is_json:
        return jsonify({"error": "Invalid JSON"}), 400

    payload = request.get_json()
    event_type = request.headers.get("X-GitHub-Event")
    print(f"Received event: {event_type}")

    try:
        data = None

        # Handle PUSH
        if event_type == "push":
            head_commit = payload.get("head_commit")
            if head_commit is None or "timestamp" not in head_commit:
                return jsonify({"error": "No head_commit timestamp in push event"}), 200

            data = {
                "action": "push",
                "author": payload.get("pusher", {}).get("name", "unknown"),
                "to_branch": payload.get("ref", "").split("/")[-1],
                "timestamp": datetime.strptime(head_commit.get("timestamp", ""), "%Y-%m-%dT%H:%M:%SZ")
            }

        # Handle PULL REQUEST
        elif event_type == "pull_request":
            pr = payload.get("pull_request", {})
            action_type = payload.get("action")

            if action_type == "opened":
                data = {
                    "action": "pull_request",
                    "author": pr.get("user", {}).get("login", "unknown"),
                    "from_branch": pr.get("head", {}).get("ref", "unknown"),
                    "to_branch": pr.get("base", {}).get("ref", "unknown"),
                    "timestamp": datetime.strptime(pr.get("created_at", ""), "%Y-%m-%dT%H:%M:%SZ")
                }

            elif action_type == "closed" and pr.get("merged"):
                data = {
                    "action": "merge",
                    "author": pr.get("user", {}).get("login", "unknown"),
                    "from_branch": pr.get("head", {}).get("ref", "unknown"),
                    "to_branch": pr.get("base", {}).get("ref", "unknown"),
                    "timestamp": datetime.strptime(pr.get("merged_at", ""), "%Y-%m-%dT%H:%M:%SZ")
                }

        # Insert data if valid
        if data:
            collection.insert_one(data)
            print("✅ Event stored:", data)
            return jsonify({"message": f"{data['action']} event stored"}), 200
        else:
            return jsonify({"message": "Ignored event or missing data"}), 200

    except Exception as e:
        print("❌ ERROR:", str(e))
        return jsonify({"error": str(e)}), 500

# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True, port=5000)

