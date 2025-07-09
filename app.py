from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from datetime import datetime
import pytz

app = Flask(__name__)

# ✅ MongoDB Atlas connection (with password properly encoded)
client = MongoClient("mongodb+srv://dbuser:Bharu%40446@cluster0.gt4fbl2.mongodb.net/?retryWrites=true&w=majority")
db = client["webhooks"]
collection = db["events"]

# ✅ Utility: UTC timestamp with formatting
def format_timestamp():
    india_tz = pytz.timezone("Asia/Kolkata")
    now = datetime.now(india_tz)
    return now.strftime("%d %B %Y - %I:%M %p IST")

# ✅ Home route
@app.route('/')
def home():
    return render_template('index.html')

# ✅ Webhook endpoint
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
            action = data.get('action')
            pr = data.get('pull_request', {})
            if action in ['opened', 'reopened'] and pr:
                parsed_event = {
                    "type": "pull_request",
                    "author": pr.get('user', {}).get('login'),
                    "from_branch": pr.get('head', {}).get('ref'),
                    "to_branch": pr.get('base', {}).get('ref'),
                    "timestamp": format_timestamp()
                }

        elif event_type == 'merge':
            # Optional: You can remove this if you're not manually handling merge events
            parsed_event = {
                "type": "merge",
                "author": data.get('sender', {}).get('login'),
                "from_branch": data.get('from'),
                "to_branch": data.get('to'),
                "timestamp": format_timestamp()
            }

        # ✅ Log & Insert
        if parsed_event:
            print("✅ Parsed Event:", parsed_event)
            collection.insert_one(parsed_event)
            print("✅ INSERT SUCCESS")
        else:
            print("⚠️ No data parsed for this event")

        return '', 204

    except Exception as e:
        print(f"❌ Error processing webhook: {e}")
        return jsonify({"error": str(e)}), 500

# ✅ API to fetch latest event
@app.route('/events', methods=['GET'])
def get_latest_event():
    try:
        event = collection.find().sort('_id', -1).limit(1)
        return jsonify([doc for doc in event])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)

