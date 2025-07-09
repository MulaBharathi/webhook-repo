from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from datetime import datetime, timezone

app = Flask(__name__)

# MongoDB Connection
client = MongoClient("mongodb+srv://dbuser:Bharu%40446@cluster0.gt4fbl2.mongodb.net/?retryWrites=true&w=majority")
db = client["webhooks"]
collection = db["events"]

# Function to format UTC timestamp
def format_timestamp():
    return datetime.now(timezone.utc).strftime("%d %B %Y - %I:%M %p UTC")

# Home route to render UI
@app.route('/')
def home():
    return render_template('index.html')

# Route to handle GitHub Webhooks
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        event_type = request.headers.get('X-GitHub-Event')
        print(f"\n📥 Event Type: {event_type}")
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
            user = pr.get('user', {})
            base = pr.get('base', {})
            head = pr.get('head', {})
            if action == 'opened' and user and base and head:
                parsed_event = {
                    "type": "pull_request",
                    "author": user.get('login'),
                    "from_branch": head.get('ref'),
                    "to_branch": base.get('ref'),
                    "timestamp": format_timestamp()
                }

        elif event_type == 'pull_request' and data.get('action') == 'closed':
            if data.get('pull_request', {}).get('merged'):
                user = data['pull_request']['user']['login']
                from_branch = data['pull_request']['head']['ref']
                to_branch = data['pull_request']['base']['ref']
                parsed_event = {
                    "type": "merge",
                    "author": user,
                    "from_branch": from_branch,
                    "to_branch": to_branch,
                    "timestamp": format_timestamp()
                }

        if parsed_event:
            print("✅ Inserting into MongoDB:", parsed_event)
            collection.insert_one(parsed_event)
            return '', 204
        else:
            print("⚠️ No relevant data to store.")
            return '', 204

    except Exception as e:
        print(f"❌ Error processing webhook: {e}")
        return jsonify({"error": str(e)}), 500

# Route to get latest event for UI polling
@app.route('/events', methods=['GET'])
def get_latest_event():
    try:
        event = collection.find().sort('_id', -1).limit(1)
        return jsonify([doc for doc in event])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)


