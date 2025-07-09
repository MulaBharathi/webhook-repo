from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from datetime import datetime, timezone
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# MongoDB Connection (update with your credentials)
client = MongoClient("mongodb+srv://dbuser:Bharu%40446@cluster0.gt4fbl2.mongodb.net/?retryWrites=true&w=majority")
db = client["webhooks"]
collection = db["events"]

# Helper function for formatted timestamp
def format_timestamp():
    now = datetime.now(timezone.utc)
    return now.strftime("%d %B %Y - %I:%M %p UTC")

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        event_type = request.headers.get('X-GitHub-Event')
        print(f"\U0001F4E5 Event Type: {event_type}")
        print(f"\U0001F4E6 Full Payload: {data}")

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
            if pr:
                parsed_event = {
                    "type": "pull_request",
                    "author": pr.get('user', {}).get('login'),
                    "from_branch": pr.get('head', {}).get('ref'),
                    "to_branch": pr.get('base', {}).get('ref'),
                    "timestamp": format_timestamp()
                }

        elif event_type == 'merge':
            # Optional: Only if merge events are set up
            pass

        if parsed_event:
            print(f"✅ Parsed Event: {parsed_event}")
            collection.insert_one(parsed_event)
            print("🗃️ Saved to MongoDB")
            return '', 204
        else:
            print("⚠️ Event ignored or missing required fields")
            return '', 204

    except Exception as e:
        print(f"❌ Error processing webhook: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/events')
def get_latest_event():
    try:
        latest = collection.find().sort("_id", -1).limit(1)
        event = next(latest, None)
        return jsonify(event if event else {})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)

