import os
from datetime import datetime, timedelta

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# --- Database URL (Render gives postgres://... sometimes) ---
raw_db_url = os.getenv("DATABASE_URL", "")
if raw_db_url.startswith("postgres://"):
    raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = raw_db_url or "sqlite:///local.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# --- Model: subscription tokens ---
class Token(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(100), unique=True, nullable=False)
    active = db.Column(db.Boolean, default=True)
    expires = db.Column(db.DateTime, nullable=True)  # None = no expiry

    def is_valid(self) -> bool:
        if not self.active:
            return False
        if self.expires and self.expires < datetime.utcnow():
            return False
        return True

# --- Seed helper: create tokens from env on startup ---
def seed_tokens_from_env():
    """
    Set env var DEFAULT_TOKENS with comma-separated tokens, e.g.:
      DEFAULT_TOKENS=DEMO-123,VIP-ABC,TRIAL-XYZ
    Optional: TOKEN_TTL_DAYS=365  (expiry in days; omit for no expiry)
    """
    tokens_csv = os.getenv("DEFAULT_TOKENS", "").strip()
    if not tokens_csv:
        return

    ttl_days = os.getenv("TOKEN_TTL_DAYS")
    expires = None
    if ttl_days:
        try:
            expires = datetime.utcnow() + timedelta(days=int(ttl_days))
        except ValueError:
            pass  # ignore bad TTL and just create non-expiring

    for t in [s.strip() for s in tokens_csv.split(",") if s.strip()]:
        if not Token.query.filter_by(token=t).first():
            db.session.add(Token(token=t, active=True, expires=expires))
    db.session.commit()

# --- Create tables & seed on import (works under gunicorn on Render) ---
with app.app_context():
    db.create_all()
    seed_tokens_from_env()

# --- Routes ---
@app.route("/")
def home():
    return (
        "✅ Subscription API is running. "
        "Check tokens with /check?token=<YOUR_TOKEN>"
    )

@app.route("/check")
def check():
    token_value = request.args.get("token")
    if not token_value:
        return jsonify({"error": "Missing ?token=<subscription_token>"}), 400

    token = Token.query.filter_by(token=token_value).first()
    if not token:
        return jsonify({"token": token_value, "valid": False, "message": "Token not found"}), 404

    if not token.is_valid():
        # Tell the client *why* it failed
        if not token.active:
            return jsonify({"token": token_value, "valid": False, "message": "Token inactive"}), 403
        if token.expires and token.expires < datetime.utcnow():
            return jsonify({"token": token_value, "valid": False, "message": "Token expired"}), 403

    return jsonify({
        "token": token_value,
        "valid": True,
        "expires": token.expires.isoformat() if token.expires else None
    })

# Dev server (Render uses gunicorn; this only runs locally)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
