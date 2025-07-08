from flask import Flask, request
from pymongo import MongoClient
from datetime import datetime
import os
import traceback
from dotenv import load_dotenv

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
print("✅ Connected to MongoDB")

# Timestamp formatter
def format_timestamp(ts):
    try:
        if ts:
            try:
                dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%fZ")
            return dt.strftime("%-d %B %Y - %-I:%M %p UTC")
    except Exception:
        pass
    return datetime.utcnow().strftime("%-d %B %Y - %-I:%M %p UTC")

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        payload = request.get_json()
        event_type = request.headers.get("X-GitHub-Event", "unknown")
        print(f"📥 Event: {event_type}")
        print("📦 Payload:", payload)

        result = {}

        # PUSH event
        if event_type == "push":
            author = payload.get("pusher", {}).get("name", "unknown")
            to_branch = payload.get("ref", "").split("/")[-1]
            timestamp = payload.get("head_commit", {}).get("timestamp", "")
            formatted_time = format_timestamp(timestamp)

            result = {
                "type": "push",
                "author": author,
                "to_branch": to_branch,
                "timestamp": formatted_time,
                "message": f'"{author}" pushed to "{to_branch}" on {formatted_time}'
            }

        # PULL REQUEST (opened)
        elif event_type == "pull_request":
            action = payload.get("action")
            pr = payload.get("pull_request", {})
            if action == "opened":
                author = pr.get("user", {}).get("login", "unknown")
                from_branch = pr.get("head", {}).get("ref", "")
                to_branch = pr.get("base", {}).get("ref", "")
                timestamp = pr.get("created_at", "")
                formatted_time = format_timestamp(timestamp)

                result = {
                    "type": "pull_request",
                    "author": author,
                    "from_branch": from_branch,
                    "to_branch": to_branch,
                    "timestamp": formatted_time,
                    "message": f'"{author}" submitted a pull request from "{from_branch}" to "{to_branch}" on {formatted_time}'
                }

            # MERGE (pull_request closed and merged = true)
            elif action == "closed" and pr.get("merged"):
                author = pr.get("user", {}).get("login", "unknown")
                from_branch = pr.get("head", {}).get("ref", "")
                to_branch = pr.get("base", {}).get("ref", "")
                timestamp = pr.get("merged_at", "")
                formatted_time = format_timestamp(timestamp)

                result = {
                    "type": "merge",
                    "author": author,
                    "from_branch": from_branch,
                    "to_branch": to_branch,
                    "timestamp": formatted_time,
                    "message": f'"{author}" merged branch "{from_branch}" to "{to_branch}" on {formatted_time}'
                }

        if result:
            collection.insert_one(result)
            print("✅ Stored:", result)
            return "Success", 200
        else:
            print("⚠️ Ignored event or unsupported action.")
            return "No action", 200

    except Exception as e:
        print("❌ Error:", e)
        traceback.print_exc()
        return "Server Error", 500

if __name__ == "__main__":
    app.run(port=5000, debug=True)

