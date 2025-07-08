from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# MongoDB configuration
mongo_uri = os.getenv("MONGO_URI")
mongo_db = os.getenv("MONGO_DB")
mongo_collection = os.getenv("MONGO_COLLECTION")

client = MongoClient(mongo_uri)
db = client[mongo_db]
collection = db[mongo_collection]

@app.route('/')
def index():
    latest_event = collection.find_one({"timestamp": {"$exists": True}}, sort=[("timestamp", -1)])
    return render_template('index.html', data=latest_event)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        payload = request.get_json(force=True)
        if not payload:
            print("❌ Invalid or missing JSON payload")
            return "Invalid JSON", 400

        event_type = request.headers.get('X-GitHub-Event', 'unknown')
        print(f"\n🔔 Received event: {event_type}")

        doc = {
            "event": event_type,
            "received_at": datetime.utcnow()
        }

        if event_type == 'push':
            doc["action"] = "push"
            doc["author"] = payload.get("head_commit", {}).get("author", {}).get("name")
            doc["to_branch"] = payload.get("ref", "").split("/")[-1]

            ts = payload.get("head_commit", {}).get("timestamp")
            if ts:
                try:
                    doc["timestamp"] = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
                except ValueError:
                    print("⚠️ Invalid timestamp format in push event")

        elif event_type == 'pull_request':
            pr = payload.get("pull_request", {})
            doc["action"] = "pull_request"
            doc["author"] = pr.get("user", {}).get("login")
            doc["to_branch"] = pr.get("base", {}).get("ref")

            ts = pr.get("created_at")
            if ts:
                try:
                    doc["timestamp"] = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
                except ValueError:
                    print("⚠️ Invalid timestamp format in pull_request event")

        else:
            doc["note"] = f"Unhandled event type: {event_type}"

        collection.insert_one(doc)
        print("✅ Event saved to MongoDB")

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print(f"❌ Exception: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5000, debug=True)

