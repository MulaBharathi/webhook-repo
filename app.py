from flask import Flask, request, render_template, jsonify
import json
import datetime

app = Flask(__name__)

@app.route('/')
def index():
    try:
        with open('webhook_data.json', 'r') as f:
            data = json.load(f)
    except:
        data = {}

    return render_template('index.html', data=data)

@app.route('/webhook', methods=['POST'])
def webhook():
    payload = request.get_json()
    payload['received_at'] = datetime.datetime.now().isoformat()

    with open('webhook_data.json', 'w') as f:
        json.dump(payload, f, indent=2)

    return 'Webhook received!', 200

@app.route('/webhook-data')
def get_data():
    try:
        with open('webhook_data.json', 'r') as f:
            data = json.load(f)
        return jsonify(data)
    except:
        return jsonify({})

if __name__ == '__main__':
    app.run(debug=True)

