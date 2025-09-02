from flask import Flask, request, jsonify
import datetime

app = Flask(__name__)

# Example database (you’ll replace with real DB later)
subscriptions = {
    "user1": {"expires": "2025-09-30"},
    "user2": {"expires": "2025-10-10"}
}

@app.route("/check", methods=["GET"])
def check_subscription():
    user = request.args.get("user")
    if not user:
        return jsonify({"error": "No user provided"}), 400

    sub = subscriptions.get(user)
    if not sub:
        return jsonify({"status": "inactive"})

    today = datetime.date.today()
    expires = datetime.datetime.strptime(sub["expires"], "%Y-%m-%d").date()

    if today <= expires:
        return jsonify({"status": "active", "expires": str(expires)})
    else:
        return jsonify({"status": "expired", "expires": str(expires)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
