from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)

# MongoDB Connection
client = MongoClient("mongodb+srv://dbuser:Bharu%40446@cluster0.gt4fbl2.mongodb.net/?retryWrites=true&w=majority")
db = client["webhooks"]
collection = db["events"]

# Format timestamp in UTC (cross-platform)
def format_timestamp():
    now = datetime.utcnow()
    day = now.day
    suffix = 'th' if 11 <= day <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
    hour = now.strftime("%I").lstrip("0")  # remove leading 0
    minute = now.strftime("%M")
    am_pm = now.strftime("%p")
    date_str = f"{day}{suffix} {now.strftime('%B %Y')} - {hour}:{minute} {am_pm} UTC"
    return date_str

# UI route
@app.route('/')
def index():
    return render_template('index.html')

# Webhook endpoint
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    event_type = request.headers.get('X-GitHub-Event')
    print(f"\n📥 Received event: {event_type}")
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

            elif action == 'closed' and pr.get('merged'):
                parsed_event = {
                    "type": "merge",
                    "author": pr.get('user', {}).get('login'),
                    "from_branch": pr.get('head', {}).get('ref'),
                    "to_branch": pr.get('base', {}).get('ref'),
                    "timestamp": format_timestamp()
                }

        # Insert event into MongoDB
        if parsed_event:
            collection.insert_one(parsed_event)
            print(f"✅ Event saved to DB: {parsed_event}")
            return '', 204
        else:
            print("⚠️ No valid event parsed.")
            return '', 204

    except Exception as e:
        print(f"❌ Error processing webhook: {e}")
        return jsonify({'error': str(e)}), 500

# Fetch latest event
@app.route('/events', methods=['GET'])
def get_latest_event():
    try:
        event = collection.find().sort('_id', -1).limit(1)
        return jsonify([doc for doc in event])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Run app
if __name__ == '__main__':
    app.run(debug=True, port=5000)

