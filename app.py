from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)
CORS(app)

# MongoDB connection (Atlas)
client = MongoClient("mongodb+srv://dbuser:Bharu%40446@cluster0.gt4fbl2.mongodb.net/?retryWrites=true&w=majority")
db = client["github_events"]
collection = db["events"]

# Format timestamp
def format_timestamp():
    return datetime.utcnow().strftime("%-d %B %Y - %-I:%M %p UTC")

# Webhook endpoint
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        event_type = request.headers.get('X-GitHub-Event')
        print("\n📥 Received Event:", event_type)
        print("Payload:", data)

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
            if action == 'opened':
                parsed_event = {
                    "type": "pull_request",
                    "author": pr.get('user', {}).get('login'),
                    "from_branch": pr.get('head', {}).get('ref'),
                    "to_branch": pr.get('base', {}).get('ref'),
                    "timestamp": format_timestamp()
                }
            elif action == 'closed' and pr.get('merged'):
                parsed_event = {
                    "type": "merge",
                    "author": pr.get('user', {}).get('login'),
                    "from_branch": pr.get('head', {}).get('ref'),
                    "to_branch": pr.get('base', {}).get('ref'),
                    "timestamp": format_timestamp()
                }

        if parsed_event:
            collection.insert_one(parsed_event)
            print("✅ Event stored:", parsed_event)
            return jsonify({"message": "Event stored"}), 200
        else:
            print("⚠️ Ignored event or missing data.")
            return jsonify({"message": "Ignored or unsupported event"}), 204

    except Exception as e:
        print("💥 Error in /webhook:", str(e))
        return jsonify({"error": str(e)}), 500

# Route to get latest event
@app.route('/events', methods=['GET'])
def get_latest_event():
    try:
        event = collection.find().sort('_id', -1).limit(1)
        return jsonify([doc for doc in event])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Serve index.html
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)


