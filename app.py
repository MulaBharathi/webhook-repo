from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ✅ MongoDB connection
try:
    client = MongoClient("mongodb+srv://dbuser:Bharu%40446@cluster0.gt4fbl2.mongodb.net/?retryWrites=true&w=majority")
    db = client["github_events"]
    collection = db["events"]
    print("✅ MongoDB connected. Databases:", client.list_database_names())
except Exception as e:
    print("❌ MongoDB connection failed:", e)

# ✅ Format timestamp to human-readable UTC
def format_timestamp():
    return datetime.utcnow().strftime("%-d %B %Y - %-I:%M %p UTC")

# ✅ GitHub webhook endpoint
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json(force=True)
        event_type = request.headers.get('X-GitHub-Event', 'unknown')

        print("📥 Event Type:", event_type)
        print("📦 Raw Payload:", data)

        parsed_event = {}

        if event_type == 'push':
            pusher = data.get('pusher', {})
            ref = data.get('ref', '')
            if pusher and ref:
                parsed_event = {
                    "type": "push",
                    "author": pusher.get('name', 'unknown'),
                    "to_branch": ref.split('/')[-1],
                    "timestamp": format_timestamp()
                }

        elif event_type == 'pull_request':
            action = data.get('action', '')
            pr = data.get('pull_request', {})
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

        if parsed_event:
            result = collection.insert_one(parsed_event)
            print("✅ Event stored in MongoDB. ID:", result.inserted_id)
            return jsonify({"message": "Event stored"}), 200
        else:
            print("⚠️ Ignored or unsupported event.")
            return jsonify({"message": "Ignored or unsupported event"}), 204

    except Exception as e:
        import traceback
        print("❌ Error processing webhook:", str(e))
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ✅ Fetch latest event for frontend
@app.route('/events', methods=['GET'])
def get_latest_event():
    try:
        event = collection.find().sort('_id', -1).limit(1)
        return jsonify([doc for doc in event])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ✅ Serve frontend
@app.route('/')
def index():
    return render_template('index.html')

# ✅ Run the Flask server
if __name__ == '__main__':
    app.run(debug=True)


