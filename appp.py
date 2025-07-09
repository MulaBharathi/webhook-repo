from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)
CORS(app)

# MongoDB connection (Local or Atlas)
client = MongoClient("mongodb+srv://dbuser:Bharu%40446@cluster0.gt4fbl2.mongodb.net/?retryWrites=true&w=majority")
db = client["github_events"]
collection = db["events"]

# Format timestamp to UTC human-readable
def format_timestamp():
    return datetime.utcnow().strftime("%-d %B %Y - %-I:%M %p UTC")

# GitHub webhook endpoint
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    event_type = request.headers.get('X-GitHub-Event')
    parsed_event = {}

    if event_type == 'push':
        parsed_event = {
            "type": "push",
            "author": data['pusher']['name'],
            "to_branch": data['ref'].split('/')[-1],
            "timestamp": format_timestamp()
        }

    elif event_type == 'pull_request':
        action = data.get('action')
        if action == 'opened':
            parsed_event = {
                "type": "pull_request",
                "author": data['pull_request']['user']['login'],
                "from_branch": data['pull_request']['head']['ref'],
                "to_branch": data['pull_request']['base']['ref'],
                "timestamp": format_timestamp()
            }
        elif action == 'closed' and data['pull_request']['merged']:
            parsed_event = {
                "type": "merge",
                "author": data['pull_request']['user']['login'],
                "from_branch": data['pull_request']['head']['ref'],
                "to_branch": data['pull_request']['base']['ref'],
                "timestamp": format_timestamp()
            }

    if parsed_event:
        collection.insert_one(parsed_event)
        return jsonify({"message": "Event stored"}), 200
    else:
        return jsonify({"message": "Ignored or unsupported event"}), 204

# Route to fetch latest event for the frontend
@app.route('/events', methods=['GET'])
def get_latest_event():
    event = collection.find().sort('_id', -1).limit(1)
    return jsonify([doc for doc in event])

# Serve frontend
@app.route('/')
def index():
    return render_template('index.html')

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)

