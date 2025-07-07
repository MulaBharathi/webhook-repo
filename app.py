from flask import Flask, request, render_template, jsonify
from pymongo import MongoClient
import datetime

app = Flask(__name__)

# Connect to MongoDB Atlas or local MongoDBi
client = MongoClient("mongodb+srv://dbuser:Bharu%40446@cluster0.gt4fbl2.mongodb.net/webhook?retryWrites=true&w=majority")  # 🔁 Replace with your actual URI
db = client["webhooks"]
collection = db["events"]

@app.route('/')
def index():
    # Get the most recent event
    data = collection.find_one(sort=[("received_at", -1)])
    return render_template('index.html', data=data)

@app.route('/webhook', methods=['POST'])
def webhook():
    payload = request.get_json()
    action_type = None

    if 'pull_request' in payload:
        pr = payload['pull_request']
        if payload.get("action") == "opened":
            action_type = "pull_request"
            payload = {
                "action": "pull_request",
                "author": pr["user"]["login"],
                "from_branch": pr["head"]["ref"],
                "to_branch": pr["base"]["ref"],
                "timestamp": pr["created_at"],
                "received_at": datetime.datetime.utcnow().isoformat()
            }
        elif payload.get("action") == "closed" and pr.get("merged"):
            action_type = "merge"
            payload = {
                "action": "merge",
                "author": pr["user"]["login"],
                "from_branch": pr["head"]["ref"],
                "to_branch": pr["base"]["ref"],
                "timestamp": pr["merged_at"],
                "received_at": datetime.datetime.utcnow().isoformat()
            }
    elif 'head_commit' in payload:
        action_type = "push"
        payload = {
            "action": "push",
            "author": payload["pusher"]["name"],
            "to_branch": payload["ref"].split("/")[-1],
            "timestamp": payload["head_commit"]["timestamp"],
            "received_at": datetime.datetime.utcnow().isoformat()
        }

    if action_type:
        collection.insert_one(payload)

    return 'Webhook received!', 200


@app.route('/webhook-data')
def get_data():
    data = collection.find_one(sort=[("received_at", -1)])
    return jsonify(data if data else {})

if __name__ == '__main__':
    app.run(debug=True)

