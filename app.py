from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv
import os
import traceback

# Load environment variables
load_dotenv()

app = Flask(__name__)

# MongoDB config
mongo_uri = os.getenv("MONGO_URI")
mongo_db = os.getenv("MONGO_DB")
mongo_collection = os.getenv("MONGO_COLLECTION")

client = MongoClient(mongo_uri)
db = client[mongo_db]
collection = db[mongo_collection]

# Home UI route
@app.route("/")
def index():
    latest = collection.find_one(sort=[("timestamp", -1)])
    return render_template("index.html", data=latest)

# Webhook endpoint
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        print("========== NEW WEBHOOK ==========")
        print("Headers:", dict(request.headers))
        print("Raw data:", request.data.decode("utf-8"))

        if not request.is_json:
            return jsonify({"error": "Invalid JSON"}), 400

        payload = request.get_json()
        event_type = request.headers.get("X-GitHub-Event")
        print("Event Type:", event_type)
        print("Payload:", payload)

        data = None

        # Handle PUSH event
        if event_type == "push":
            head_commit = payload.get("head_commit", {})
            timestamp = head_commit.get("timestamp")
            if not timestamp:
                return jsonify({"error": "Missing timestamp in push event"}), 200

            data = {
                "action": "push",
                "author": payload.get("pusher", {}).get("name", "unknown"),
                "to_branch": payload.get("ref", "").split("/")[-1],
                "timestamp": datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
            }

        # Handle PULL REQUEST events
        elif event_type == "pull_request":
            pr = payload.get("pull_request", {})
            action_type = payload.get("action")

            if action_type == "opened":
                timestamp = pr.get("created_at")
                if not timestamp:
                    return jsonify({"error": "Missing created_at in PR opened"}), 200

                data = {
                    "action": "pull_request",
                    "author": pr.get("user", {}).get("login", "unknown"),
                    "from_branch": pr.get("head", {}).get("ref", "unknown"),
                    "to_branch": pr.get("base", {}).get("ref", "unknown"),
                    "timestamp": datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
                }

            elif action_type == "closed" and pr.get("merged"):
                timestamp = pr.get("merged_at")
                if not timestamp:
                    return jsonify({"error": "Missing merged_at in PR merge"}), 200

                data = {
                    "action": "merge",
                    "author": pr.get("user", {}).get("login", "unknown"),
                    "from_branch": pr.get("head", {}).get("ref", "unknown"),
                    "to_branch": pr.get("base", {}).get("ref", "unknown"),
                    "timestamp": datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
                }

        # Store to MongoDB
        if data:
            collection.insert_one(data)
            print("✅ Stored to DB:", data)
            return jsonify({"message": f"{data['action']} event stored"}), 200
        else:
            print("ℹ️ Event skipped or not relevant")
            return jsonify({"message": "Ignored event or missing fields"}), 200

    except Exception as e:
        print("❌ ERROR OCCURRED")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)

