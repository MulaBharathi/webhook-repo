from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from datetime import datetime, timezone
import os

app = Flask(__name__)

# MongoDB connection
client = MongoClient("mongodb+srv://dbuser:Bharu%40446@cluster0.gt4fbl2.mongodb.net/?retryWrites=true&w=majority")
db = client["webhooks"]
collection = db["events"]

# Format current UTC timestamp
def format_timestamp():
    return datetime.now(timezone.utc).strftime("%d %B %Y - %I:%M %p UTC")

# Webhook endpoint
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        event_type = request.headers.get('X-GitHub-Event')
        print(f"📥 Event Type: {event_type}")
        print("📦 Raw Payload:", data)

        parsed_event = {}

        if event_type == 'push':
            pusher = data.get('pusher', {})
            ref = data.get('ref', '')
            if pusher and ref:
                parsed_event = {
                    "type": "push",
                    "author": pusher.get('name'),
                    "to_branch": ref.split('/')[-1],
                    "timestamp": format_timestamp()
                }

        elif event_type == 'pull_request':
            pr = data.get('pull_request', {})
            action = data.get('action', '')
            if pr:
                parsed_event = {
                    "type": "pull_request",
                    "author": pr.get('user', {}).get('login'),
                    "action": action,
                    "title": pr.get('title'),
                    "timestamp": format_timestamp()
                }

        # You can add more event types here if needed

        if parsed_event:
            collection.insert_one(parsed_event)
            print("✅ Successfully inserted event to MongoDB.")
            return '', 204
        else:
            print("⚠️ No valid event data found.")
            return '', 204

    except Exception as e:
        print(f"❌ Error processing webhook: {e}")
        return jsonify({"error": str(e)}), 500

# Route to return latest event
@app.route('/events', methods=['GET'])
def get_latest_event():
    try:
        event = collection.find().sort('_id', -1).limit(1)
        return jsonify([doc for doc in event])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Route to render UI
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)

