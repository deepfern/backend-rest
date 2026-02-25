""""Flask API application for managing records."""
from datetime import datetime, timezone
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
CORS(app)  # Enable CORS for frontend integration


# ---------- Helpers ----------

def iso_utc_z(dt: datetime | None) -> str | None:
    """
    Return ISO-8601 string with milliseconds and trailing 'Z' (UTC), e.g. 2024-11-01T10:23:45.123Z
    """
    if not dt:
        return None
    # Ensure UTC and format with milliseconds
    dt = dt.astimezone(timezone.utc).replace(tzinfo=timezone.utc)
    s = dt.isoformat(timespec="milliseconds")
    # Normalize '+00:00' to 'Z'
    if s.endswith("+00:00"):
        s = s[:-6] + "Z"
    elif not s.endswith("Z"):
        s += "Z"
    return s


# ---------- Data model ----------

class Record(db.Model):
    """Database model for records."""

    __tablename__ = 'records'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    note = db.Column(db.Text, nullable=True)
    # Use timezone-aware datetimes (UTC)
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

    # CHANGED: return camelCase keys and ISO-8601 with 'Z'
    def to_api_dict(self) -> dict:
        """Convert object to dictionary for API responses (camelCase + ISO-8601 UTC)."""
        return {
            'id': self.id,
            'name': self.name,
            'message': self.message,
            'note': self.note,
            'createdAt': iso_utc_z(self.created_at),
            'updatedAt': iso_utc_z(self.updated_at),
        }

    def update_from_dict(self, data: dict):
        """Update record fields from dictionary."""
        if 'name' in data and isinstance(data['name'], str) and data['name'].strip():
            self.name = data['name'].strip()
        if 'message' in data and isinstance(data['message'], str) and data['message'].strip():
            self.message = data['message'].strip()
        if 'note' in data:
            self.note = (data['note'].strip() if isinstance(data['note'], str) and data['note'] else None)
        # set updated_at to timezone-aware UTC now
        self.updated_at = datetime.now(timezone.utc)


# ---------- API endpoints ----------

@app.route('/')
def health_check():
    """Check API health status."""
    return jsonify({
        'status': 'OK',
        'message': 'Flask API is running',
        'timestamp': iso_utc_z(datetime.now(timezone.utc))  # CHANGED: Z-suffixed ISO
    })


# ADDED: create a new record
@app.route('/api/records', methods=['POST'])
def create_record():
    """
    Create a new record.
    Expected JSON: { "name": "John Doe", "message": "Your message here", "note": "Optional note" }
    """
    try:
        data = request.get_json(silent=True) or {}
        name = (data.get('name') or '').strip()
        message = (data.get('message') or '').strip()
        note = data.get('note')
        note = note.strip() if isinstance(note, str) and note else None

        if not name or not message:
            return jsonify({'error': 'Both "name" and "message" are required and must be non-empty strings.'}), 400

        record = Record(name=name, message=message, note=note)
        db.session.add(record)
        db.session.commit()

        return jsonify({'record': record.to_api_dict()}), 201
    except SQLAlchemyError as database_error:
        db.session.rollback()
        return jsonify({'error': f'Failed to create record: {str(database_error)}'}), 500


# ADDED: list all records in required format
@app.route('/api/records', methods=['GET'])
def list_records():
    """
    Return all records.
    Response:
    {
      "records": [ {id, name, message, note, createdAt, updatedAt}, ... ],
      "total": <int>
    }
    """
    try:
        records = Record.query.order_by(Record.id.asc()).all()
        payload = [r.to_api_dict() for r in records]
        return jsonify({'records': payload, 'total': len(payload)}), 200
    except SQLAlchemyError as database_error:
        return jsonify({'error': f'Failed to fetch records: {str(database_error)}'}), 500


# CHANGED: fix HTML-escaped route; use real Flask variable syntax
@app.route('/api/records/<int:record_id>', methods=['PUT'])
def update_record(record_id):
    """Update record by ID."""
    try:
        record = Record.query.get_or_404(record_id)
        data = request.get_json(silent=True)

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        record.update_from_dict(data)
        db.session.commit()

        return jsonify({
            'message': 'Record updated successfully',
            'record': record.to_api_dict()
        }), 200

    except (SQLAlchemyError, ValueError) as database_error:
        db.session.rollback()
        return jsonify({
            'error': f'Failed to update record: {str(database_error)}'
        }), 500


# CHANGED: fix HTML-escaped route; use real Flask variable syntax
@app.route('/api/records/<int:record_id>', methods=['DELETE'])
def delete_record(record_id):
    """Delete record by ID."""
    try:
        record = Record.query.get_or_404(record_id)
        db.session.delete(record)
        db.session.commit()

        return jsonify({'message': 'Record deleted successfully'}), 200

    except SQLAlchemyError as database_error:
        db.session.rollback()
        return jsonify({
            'error': f'Failed to delete record: {str(database_error)}'
        }), 500


# ---------- Error handlers ----------

@app.errorhandler(404)
def not_found(_error):
    """Handle 404 errors."""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(_error):
    """Handle 500 errors."""
    return jsonify({'error': 'Internal server error'}), 500


# ---------- DB bootstrap ----------

def create_tables():
    """Create database tables."""
    try:
        with app.app_context():
            db.create_all()
            print("Database tables created successfully!")
    except SQLAlchemyError as database_error:
        print(f"Error creating database tables: {database_error}")


if __name__ == '__main__':
    # Create tables on startup
    create_tables()

    # Run Flask application
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
