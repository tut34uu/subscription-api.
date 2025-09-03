from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime

app = Flask(__name__)

# Get database URL from environment
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Database model for subscription tokens
class Token(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(100), unique=True, nullable=False)
    active = db.Column(db.Boolean, default=True)
    expires = db.Column(db.DateTime, nullable=True)

@app.route("/")
def home():
    return "✅ Subscription API is running! Use /check?token=<subscription_token>"

@app.route("/check")
def check():
    token_value = request.args.get("token")
    if not token_value:
        return jsonify({"error": "Missing ?token=<subscription_token>"}), 400

    token = Token.query.filter_by(token=token_value).first()
    if not token:
        return jsonify({"token": token_value, "valid": False, "message": "Token not found"}), 404

    if not token.active:
        return jsonify({"token": token_value, "valid": False, "message": "Token inactive"}), 403

    if token.expires and token.expires < datetime.utcnow():
        return jsonify({"token": token_value, "valid": False, "message": "Token expired"}), 403

    return jsonify({"token": token_value, "valid": True, "expires": token.expires})

# Admin helper: add token manually (for testing)
@app.route("/add_token", methods=["POST"])
def add_token():
    data = request.json
    new_token = Token(
        token=data["token"],
        active=data.get("active", True),
        expires=datetime.strptime(data["expires"], "%Y-%m-%d") if data.get("expires") else None
    )
    db.session.add(new_token)
    db.session.commit()
    return jsonify({"message": f"Token {data['token']} added."})

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000)
