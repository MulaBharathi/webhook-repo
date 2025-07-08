from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# MongoDB setup
client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB")]
collection = db[os.getenv("MONGO_COLLECTION")]

@app.route('/')
def index():
    latest = collection.find_one(sort=[('_id', -1)])
    return render_template('index.html', data=latest)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        payload = request.get_json(force=True)
        event = request.headers.get('X-GitHub-Event')

        doc = {
            "event": event,
            "received_at": datetime.utcnow()
        }

        if event == 'push':
            doc.update({
                "action": "push",
                "author": payload.get('head_commit', {}).get('author', {}).get('name'),
                "to_branch": payload.get('ref', '').split('/')[-1],
                "timestamp": datetime.strptime(
                    payload.get('head_commit', {}).get('timestamp', ''),
                    "%Y-%m-%dT%H:%M:%SZ"
                )
            })

        elif event == 'pull_request':
            pr = payload.get('pull_request', {})
            doc.update({
                "action": "pull_request",
                "author": pr.get('user', {}).get('login'),
                "to_branch": pr.get('base', {}).get('ref'),
                "timestamp": datetime.strptime(
                    pr.get('created_at', ''),
                    "%Y-%m-%dT%H:%M:%SZ"
                )
            })

        else:
            doc['note'] = f"Unhandled event: {event}"

        collection.insert_one(doc)
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)

