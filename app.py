""""Flask API application for managing records."""
from datetime import datetime, timezone
from typing import Optional
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from sqlalchemy.exc import SQLAlchemyError
from config import Config

# Initialize Flask application
app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db = SQLAlchemy(app)
CORS(app)


# ---------- Helpers ----------

def iso_utc_z(dt: datetime | None) -> str | None:
    """Convert datetime to ISO-8601 UTC format with trailing 'Z'."""
    if not dt:
        return None

    dt = dt.astimezone(timezone.utc).replace(tzinfo=timezone.utc)
    s = dt.isoformat(timespec="milliseconds")

    if s.endswith("+00:00"):
        return s[:-6] + "Z"
    if not s.endswith("Z"):
        return s + "Z"
    return s


# ---------- Data model ----------

class Record(db.Model):
    """Database model for records."""
    __tablename__ = "records"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def to_api_dict(self) -> dict:
        """Convert record to API dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "message": self.message,
            "note": self.note,
            "createdAt": iso_utc_z(self.created_at),
            "updatedAt": iso_utc_z(self.updated_at),
        }

    def update_from_dict(self, data: dict):
        """Update record from incoming JSON."""
        if "name" in data and isinstance(data["name"], str) and data["name"].strip():
            self.name = data["name"].strip()
        if "message" in data and isinstance(data["message"], str) and data["message"].strip():
            self.message = data["message"].strip()
        if "note" in data:
            note = data["note"]
            self.note = note.strip() if isinstance(note, str) and note else None

        self.updated_at = datetime.now(timezone.utc)


# ---------- API endpoints ----------

@app.route("/")
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "OK",
        "message": "Flask API is running",
        "timestamp": iso_utc_z(datetime.now(timezone.utc)),
    })


@app.route("/api/records", methods=["POST"])
def create_record():
    """Create a new record."""
    try:
        data = request.get_json(silent=True) or {}
        name = (data.get("name") or "").strip()
        message = (data.get("message") or "").strip()
        note_raw = data.get("note")
        note = note_raw.strip() if isinstance(note_raw, str) and note_raw else None

        if not name or not message:
            return jsonify(
                {"error": 'Both "name" and "message" must be non-empty strings.'}
            ), 400

        record = Record(name=name, message=message, note=note)
        db.session.add(record)
        db.session.commit()
        return jsonify({"record": record.to_api_dict()}), 201

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to create record: {e}"}), 500


@app.route("/api/records", methods=["GET"])
def list_records():
    """Return all records."""
    try:
        records = Record.query.order_by(Record.id.asc()).all()
        payload = [r.to_api_dict() for r in records]
        return jsonify({"records": payload, "total": len(payload)})
    except SQLAlchemyError as e:
        return jsonify({"error": f"Failed to fetch records: {e}"}), 500


@app.route("/api/records/<int:record_id>", methods=["PUT"])
def update_record(record_id):
    """Update record by ID."""
    try:
        record = Record.query.get_or_404(record_id)
        data = request.get_json(silent=True)

        if not data:
            return jsonify({"error": "No data provided"}), 400

        record.update_from_dict(data)
        db.session.commit()
        return jsonify({
            "message": "Record updated successfully",
            "record": record.to_api_dict()
        })

    except (SQLAlchemyError, ValueError) as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to update record: {e}"}), 500


@app.route("/api/records/<int:record_id>", methods=["DELETE"])
def delete_record(record_id):
    """Delete record by ID."""
    try:
        record = Record.query.get_or_404(record_id)
        db.session.delete(record)
        db.session.commit()
        return jsonify({"message": "Record deleted successfully"})

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to delete record: {e}"}), 500


# ---------- Error handlers ----------

@app.errorhandler(404)
def not_found(_):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(_):
    return jsonify({"error": "Internal server error"}), 500


# ---------- DB bootstrap ----------

def create_tables():
    """Create database tables."""
    try:
        with app.app_context():
            db.create_all()
    except SQLAlchemyError as e:
        print(f"Error creating database tables: {e}")


if __name__ == "__main__":
    create_tables()
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)