from flask import Flask, request, jsonify, render_template
from datetime import datetime
from db import collection  # assuming you have db.py with MongoDB connection

app = Flask(__name__)

# Format: 1st July 2025 - 01:30 PM UTC
def format_timestamp():
    now = datetime.utcnow()
    day = now.day
    suffix = 'th' if 11 <= day <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
    return now.strftime(f"{day}{suffix} %B %Y - %I:%M %p UTC")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/webhook', methods=['POST'])
def webhook():
    event_type = request.headers.get('X-GitHub-Event')
    data = request.json
    print(f"📥 Event Type: {event_type}")
    print(f"📦 Payload: {data}")

    parsed_event = {}

    try:
        if event_type == 'ping':
            print("🔔 Ping event received.")
            return jsonify({'msg': 'pong'}), 200

        if event_type == 'push':
            pusher = data.get('pusher', {})
            branch = data.get('ref', '').split('/')[-1]
            parsed_event = {
                "type": "push",
                "author": pusher.get('name'),
                "to_branch": branch,
                "timestamp": format_timestamp()
            }

        elif event_type == 'pull_request':
            pr = data.get('pull_request', {})
            action = data.get('action')

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
            print("✅ Saved to DB:", parsed_event)
            return '', 204
        else:
            print("⚠️ No valid event to save.")
            return '', 204

    except Exception as e:
        print("❌ Error while processing:", e)
        return jsonify({"error": str(e)}), 500

@app.route('/events', methods=['GET'])
def get_latest_event():
    try:
        event = collection.find().sort('_id', -1).limit(1)
        return jsonify([e for e in event])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)

