from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv
import os
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

# UI route to display latest event
@app.route("/")
def index():
    latest = collection.find_one(sort=[("timestamp", -1)])
    return render_template("index.html", data=latest)

# Webhook endpoint
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        print("\n===== WEBHOOK RECEIVED =====")
        print("Headers:", dict(request.headers))
        print("Raw JSON:", request.data.decode("utf-8"))

        if not request.is_json:
            return jsonify({"error": "Invalid JSON"}), 400

        payload = request.get_json()
        event_type = request.headers.get("X-GitHub-Event")
        print("GitHub Event Type:", event_type)

        data = None

        # Handle PUSH
        if event_type == "push":
            pusher = payload.get("pusher", {}).get("name", "unknown")
            branch = payload.get("ref", "").split("/")[-1]
            head_commit = payload.get("head_commit", {})
            timestamp_str = head_commit.get("timestamp")

            if not timestamp_str:
                print("⚠️ Missing or empty timestamp in push, skipping")
                return jsonify({"message": "Ignored push with no timestamp"}), 200

            try:
                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                print("❌ Invalid timestamp format:", timestamp_str)
                return jsonify({"message": "Invalid timestamp format"}), 200

            data = {
                "action": "push",
                "author": pusher,
                "to_branch": branch,
                "timestamp": timestamp
            }

        # Handle Pull Request
        elif event_type == "pull_request":
            pr = payload.get("pull_request", {})
            action_type = payload.get("action")

            if action_type == "opened":
                timestamp_str = pr.get("created_at")
                if not timestamp_str:
                    print("⚠️ Missing created_at in PR")
                    return jsonify({"message": "Missing created_at"}), 200

                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ")

                data = {
                    "action": "pull_request",
                    "author": pr.get("user", {}).get("login", "unknown"),
                    "from_branch": pr.get("head", {}).get("ref", "unknown"),
                    "to_branch": pr.get("base", {}).get("ref", "unknown"),
                    "timestamp": timestamp
                }

            elif action_type == "closed" and pr.get("merged"):
                timestamp_str = pr.get("merged_at")
                if not timestamp_str:
                    print("⚠️ Missing merged_at in PR")
                    return jsonify({"message": "Missing merged_at"}), 200

                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ")

                data = {
                    "action": "merge",
                    "author": pr.get("user", {}).get("login", "unknown"),
                    "from_branch": pr.get("head", {}).get("ref", "unknown"),
                    "to_branch": pr.get("base", {}).get("ref", "unknown"),
                    "timestamp": timestamp
                }

        # Store valid data
        if data:
            collection.insert_one(data)
            print("✅ Event stored in MongoDB:", data)
            return jsonify({"message": f"{data['action']} event stored"}), 200
        else:
            print("ℹ️ No valid data to store")
            return jsonify({"message": "Ignored event or missing fields"}), 200

    except Exception as e:
        print("🔥 INTERNAL ERROR:", str(e))
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# Run Flask
if __name__ == "__main__":
    app.run(debug=True, port=5000)

