from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

# MongoDB Connection (use your credentials here)
client = MongoClient("mongodb+srv://dbuser:Bharu%40446@cluster0.gt4fbl2.mongodb.net/?retryWrites=true&w=majority")
db = client["github_events"]
collection = db["events"]

# Helper function to format timestamps
def format_timestamp():
    return datetime.utcnow().strftime("%-d %B %Y - %-I:%M %p UTC")

# GitHub Webhook Endpoint
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        event_type = request.headers.get('X-GitHub-Event')
        print(f"📥 Received event: {event_type}")
        parsed_event = {}

        # Handle push event
        if event_type == 'push':
            pusher = data.get('pusher', {})
            ref = data.get('ref', '')
            author = pusher.get('name', 'unknown')
            to_branch = ref.split('/')[-1] if '/' in ref else 'unknown'

            if author and to_branch:
                parsed_event = {
                    "type": "push",
                    "author": author,
                    "to_branch": to_branch,
                    "timestamp": format_timestamp()
                }

        # Handle pull_request and merge
        elif event_type == 'pull_request':
            pr = data.get('pull_request', {})
            action = data.get('action', '')
            user = pr.get('user', {}).get('login', 'unknown')
            from_branch = pr.get('head', {}).get('ref', '')
            to_branch = pr.get('base', {}).get('ref', '')

            if action == 'opened':
                parsed_event = {
                    "type": "pull_request",
                    "author": user,
                    "from_branch": from_branch,
                    "to_branch": to_branch,
                    "timestamp": format_timestamp()
                }
            elif action == 'closed' and pr.get('merged', False):
                parsed_event = {
                    "type": "merge",
                    "author": user,
                    "from_branch": from_branch,
                    "to_branch": to_branch,
                    "timestamp": format_timestamp()
                }

        # Store event if parsed
        if parsed_event:
            print("✅ Storing event:", parsed_event)
            collection.insert_one(parsed_event)
            return jsonify({"message": "Event stored"}), 200
        else:
            print("⚠️ Event ignored or unsupported")
            return jsonify({"message": "Ignored or unsupported event"}), 204

    except Exception as e:
        print("❌ Error in /webhook:", str(e))
        return jsonify({"error": str(e)}), 500

# Route to fetch latest event for frontend
@app.route('/events', methods=['GET'])
def get_latest_event():
    try:
        event = collection.find().sort('_id', -1).limit(1)
        docs = [doc for doc in event]
        print("📤 Sending event to UI:", docs)
        return jsonify(docs)
    except Exception as e:
        print("❌ Error in /events:", str(e))
        return jsonify({"error": str(e)}), 500

# Serve index.html
@app.route('/')
def index():
    return render_template('index.html')

# Run the Flask server
if __name__ == '__main__':
    app.run(debug=True)

