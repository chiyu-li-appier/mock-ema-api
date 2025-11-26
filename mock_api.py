from flask import Flask, request, jsonify
import json
import datetime
import secrets

app = Flask(__name__)

@app.route("/create_user", methods=["GET"])
def create_user():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Email is required"}), 400

    api_key = secrets.token_hex(16)
    creation_time = datetime.datetime.now().isoformat()

    user_data = {
        "email": email,
        "api_key": api_key,
        "creation_time": creation_time
    }

    with open("users.json", "a") as f:
        f.write(json.dumps(user_data) + "\n")

    return jsonify(user_data)

if __name__ == "__main__":
    app.run(debug=True)