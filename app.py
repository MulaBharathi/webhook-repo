from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)

# MongoDB Connection
client = MongoClient("mongodb+srv://dbuser:Bharu%40446@cluster0.gt4fbl2.mongodb.net/?retryWrites=true&w=majority")
db = client["webhooks"]
collection = db["events"]

def format_timestamp():
    now = datetime.utcnow()
    day = now.day
    suffix = 'th' if 11 <= day <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
    formatted = now.strftime(f"{day}{suffix} %B %Y - %-I:%M %p UTC")
    return formatted

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    event_type = request.headers.get('X-GitHub-Event')
    print(f"📥 Received event: {event_type}")
    print(f"📦 Raw Payload: {data}")

    parsed_event = {}

    try:
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
            if action == 'opened' and pr:
                parsed_event = {
                    "type": "pull_request",
                    "author": pr.get('user', {}).get('login'),
                    "from_branch": pr.get('head', {}).get('ref'),
                    "to_branch": pr.get('base', {}).get('ref'),
                    "timestamp": format_timestamp()
                }

        # Optional merge event handler if you want to support it:
        elif event_type == 'pull_request' and data.get('action') == 'closed' and data.get('pull_request', {}).get('merged'):
            pr = data.get('pull_request', {})
            parsed_event = {
                "type": "merge",
                "author": pr.get('user', {}).get('login'),
                "from_branch": pr.get('head', {}).get('ref'),
                "to_branch": pr.get('base', {}).get('ref'),
                "timestamp": format_timestamp()
            }

        # Insert if parsed
        if parsed_event:
            collection.insert_one(parsed_event)
            print(f"✅ Event saved: {parsed_event}")
            return '', 204
        else:
            print("⚠️ No valid data to save.")
            return '', 204

    except Exception as e:
        print(f"❌ Error processing webhook: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/events', methods=['GET'])
def get_latest_event():
    try:
        event = collection.find().sort('_id', -1).limit(1)
        return jsonify([doc for doc in event])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)

