from flask import Flask, request
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Flask app setup
app = Flask(__name__)

# MongoDB setup
mongo_uri = os.getenv("MONGO_URI")
mongo_db = os.getenv("MONGO_DB")
mongo_collection = os.getenv("MONGO_COLLECTION")

client = MongoClient(mongo_uri)
db = client[mongo_db]
collection = db[mongo_collection]
print("✅ Connected to MongoDB")

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        payload = request.get_json()
        event_type = request.headers.get("X-GitHub-Event", "unknown")
        print(f"📥 Event received: {event_type}")

        result = {}

        if event_type == "push":
            author = payload.get("pusher", {}).get("name", "unknown")
            to_branch = payload.get("ref", "").split("/")[-1]
            timestamp = payload.get("head_commit", {}).get("timestamp")

            # Format timestamp to readable
            formatted_time = format_timestamp(timestamp)

            result = {
                "type": "push",
                "author": author,
                "to_branch": to_branch,
                "timestamp": formatted_time,
                "message": f"{author} pushed to {to_branch} on {formatted_time}"
            }

        elif event_type == "pull_request":
            action = payload.get("action")
            if action == "opened":  # You can add more if needed
                author = payload.get("pull_request", {}).get("user", {}).get("login", "unknown")
                from_branch = payload.get("pull_request", {}).get("head", {}).get("ref", "")
                to_branch = payload.get("pull_request", {}).get("base", {}).get("ref", "")
                timestamp = payload.get("pull_request", {}).get("created_at", "")

                formatted_time = format_timestamp(timestamp)

                result = {
                    "type": "pull_request",
                    "author": author,
                    "from_branch": from_branch,
                    "to_branch": to_branch,
                    "timestamp": formatted_time,
                    "message": f"{author} submitted a pull request from {from_branch} to {to_branch} on {formatted_time}"
                }

        elif event_type == "pull_request" and payload.get("action") == "closed" and payload.get("pull_request", {}).get("merged"):
            author = payload.get("pull_request", {}).get("user", {}).get("login", "unknown")
            from_branch = payload.get("pull_request", {}).get("head", {}).get("ref", "")
            to_branch = payload.get("pull_request", {}).get("base", {}).get("ref", "")
            timestamp = payload.get("pull_request", {}).get("merged_at", "")

            formatted_time = format_timestamp(timestamp)

            result = {
                "type": "merge",
                "author": author,
                "from_branch": from_branch,
                "to_branch": to_branch,
                "timestamp": formatted_time,
                "message": f"{author} merged branch {from_branch} to {to_branch} on {formatted_time}"
            }

        if result:
            collection.insert_one(result)
            print("✅ Stored in MongoDB:", result)
            return "Stored", 200
        else:
            print("⚠️ Unsupported or incomplete event")
            return "No relevant action", 200

    except Exception as e:
        print("❌ Error in webhook:", e)
        return "Server error", 500

def format_timestamp(ts):
    try:
        dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
    except:
        try:
            dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%fZ")
        except:
            dt = datetime.utcnow()
    return dt.strftime("%-d %B %Y - %-I:%M %p UTC")

if __name__ == "__main__":
    app.run(port=5000, debug=True)

