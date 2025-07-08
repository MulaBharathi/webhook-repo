@app.route('/webhook', methods=['POST'])
def webhook():
    # Print headers and raw body for debugging
    print("========== HEADERS ==========")
    print(dict(request.headers))

    print("========== RAW BODY ==========")
    print(request.data.decode("utf-8"))

    try:
        payload = request.get_json(force=True)
    except Exception as e:
        print("[ERROR] Failed to parse JSON:", e)
        return {"message": "Failed to parse JSON"}, 400

    if not payload:
        print("[ERROR] Empty JSON payload")
        return {"message": "Empty JSON"}, 400

    print("========== PARSED PAYLOAD ==========")
    print(payload)

    return {"message": "JSON received successfully"}, 200

