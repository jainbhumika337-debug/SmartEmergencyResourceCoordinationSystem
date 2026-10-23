
from flask import Blueprint, request
from database import get_db_connection
from flask_jwt_extended import jwt_required
import uuid

emergency_bp = Blueprint("emergency", __name__)


@emergency_bp.route("/api/emergencies", methods=["POST"])
@jwt_required()
def create_emergency():
    data = request.get_json(silent=True)

    if not data:
        return {"status": "error", "message": "JSON data is required"}, 400

    required_fields = [
        "emergency_type", "description", "latitude",
        "longitude", "severity"
    ]

    for field in required_fields:
        if field not in data:
            return {
                "status": "error",
                "message": f"Missing required field: {field}"
            }, 400

    connection = None
    cursor = None

    try:
        emergency_code = "EMG-" + uuid.uuid4().hex[:10].upper()
        connection = get_db_connection()
        cursor = connection.cursor()

        query = """
            INSERT INTO emergencies (
                emergency_code, emergency_type, description,
                latitude, longitude, severity, people_affected, status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'PENDING')
        """

        values = (
            emergency_code,
            data["emergency_type"],
            data["description"],
            data["latitude"],
            data["longitude"],
            data["severity"],
            data.get("people_affected", 1)
        )

        cursor.execute(query, values)
        connection.commit()
        emergency_id = cursor.lastrowid

        return {
            "status": "success",
            "message": "Emergency registered successfully",
            "emergency_id": emergency_id,
            "emergency_code": emergency_code
        }, 201

    except Exception:
        if connection:
            connection.rollback()
        return {"status": "error", "message": "Could not create emergency"}, 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


@emergency_bp.route("/api/emergencies", methods=["GET"])
@jwt_required()
def get_emergencies():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT id, emergency_code, emergency_type, description,
                   latitude, longitude, severity, people_affected,
                   status, created_at
            FROM emergencies
            ORDER BY created_at DESC
        """)

        emergencies = cursor.fetchall()

        return {
            "status": "success",
            "total": len(emergencies),
            "emergencies": emergencies
        }, 200

    except Exception:
        return {"status": "error", "message": "Could not load emergencies"}, 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


@emergency_bp.route(
    "/api/emergencies/<int:emergency_id>/status",
    methods=["PUT"]
)
@jwt_required()
def update_emergency_status(emergency_id):
    data = request.get_json(silent=True)

    if not data or "status" not in data:
        return {"status": "error", "message": "Status is required"}, 400

    allowed_statuses = [
        "PENDING", "PROCESSING", "RESOURCES_ASSIGNED",
        "IN_PROGRESS", "RESOLVED", "CANCELLED"
    ]

    new_status = str(data["status"]).upper()

    if new_status not in allowed_statuses:
        return {"status": "error", "message": "Invalid emergency status"}, 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("SELECT id FROM emergencies WHERE id = %s", (emergency_id,))
        if cursor.fetchone() is None:
            return {"status": "error", "message": "Emergency not found"}, 404

        cursor.execute(
            "UPDATE emergencies SET status = %s WHERE id = %s",
            (new_status, emergency_id)
        )
        connection.commit()

        return {
            "status": "success",
            "message": "Emergency status updated successfully",
            "emergency_id": emergency_id,
            "new_status": new_status
        }, 200

    except Exception:
        if connection:
            connection.rollback()
        return {"status": "error", "message": "Could not update emergency"}, 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


@emergency_bp.route(
    "/api/emergencies/<int:emergency_id>/assign/<int:resource_id>",
    methods=["POST"]
)
@jwt_required()
def assign_resource(emergency_id, resource_id):
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT id, status FROM emergencies WHERE id = %s FOR UPDATE",
            (emergency_id,)
        )
        emergency = cursor.fetchone()

        if not emergency:
            connection.rollback()
            return {"status": "error", "message": "Emergency not found"}, 404

        if emergency["status"] in ("RESOLVED", "CANCELLED"):
            connection.rollback()
            return {
                "status": "error",
                "message": "Cannot assign resources to a closed emergency"
            }, 400

        cursor.execute(
            "SELECT id, resource_name, status FROM resources WHERE id = %s FOR UPDATE",
            (resource_id,)
        )
        resource = cursor.fetchone()

        if not resource:
            connection.rollback()
            return {"status": "error", "message": "Resource not found"}, 404

        if resource["status"] != "AVAILABLE":
            connection.rollback()
            return {
                "status": "error",
                "message": "Resource is not available",
                "current_status": resource["status"]
            }, 409

        cursor.execute(
            """
            INSERT INTO emergency_resources (emergency_id, resource_id, status)
            VALUES (%s, %s, 'ASSIGNED')
            """,
            (emergency_id, resource_id)
        )

        cursor.execute(
            "UPDATE resources SET status = 'ASSIGNED' WHERE id = %s",
            (resource_id,)
        )

        cursor.execute(
            """
            UPDATE emergencies SET status = 'RESOURCES_ASSIGNED'
            WHERE id = %s
              AND status IN ('PENDING', 'PROCESSING', 'RESOURCES_ASSIGNED')
            """,
            (emergency_id,)
        )

        connection.commit()

        return {
            "status": "success",
            "message": "Resource assigned successfully",
            "emergency_id": emergency_id,
            "resource_id": resource_id,
            "resource_name": resource["resource_name"],
            "new_resource_status": "ASSIGNED"
        }, 201

    except Exception:
        if connection:
            connection.rollback()
        return {"status": "error", "message": "Could not assign resource"}, 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
