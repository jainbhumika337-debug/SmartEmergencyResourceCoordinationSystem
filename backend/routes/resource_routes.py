
from flask import Blueprint, request
from database import get_db_connection
from flask_jwt_extended import jwt_required

resource_bp = Blueprint("resource", __name__)


# 1. Add a new resource
@resource_bp.route("/api/resources", methods=["POST"])
@jwt_required()
def add_resource():
    data = request.get_json(silent=True)

    if not data:
        return {"status": "error", "message": "JSON data is required"}, 400

    required_fields = [
        "resource_name",
        "resource_type_id",
        "latitude",
        "longitude"
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
        connection = get_db_connection()
        cursor = connection.cursor()

        query = """
            INSERT INTO resources (
                resource_name, resource_type_id, capacity,
                latitude, longitude, status, provider_name, provider_phone
            )
            VALUES (%s, %s, %s, %s, %s, 'AVAILABLE', %s, %s)
        """

        values = (
            data["resource_name"],
            data["resource_type_id"],
            data.get("capacity", 1),
            data["latitude"],
            data["longitude"],
            data.get("provider_name"),
            data.get("provider_phone")
        )

        cursor.execute(query, values)
        connection.commit()

        return {
            "status": "success",
            "message": "Resource added successfully",
            "resource_id": cursor.lastrowid
        }, 201

    except Exception:
        if connection:
            connection.rollback()
        return {"status": "error", "message": "Could not add resource"}, 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


# 2. Get all resources
@resource_bp.route("/api/resources", methods=["GET"])
@jwt_required()
def get_resources():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT
                r.id,
                r.resource_name,
                rt.type_name AS resource_type,
                r.capacity,
                r.latitude,
                r.longitude,
                r.status,
                r.provider_name,
                r.provider_phone
            FROM resources r
            JOIN resource_types rt ON r.resource_type_id = rt.id
            ORDER BY r.id DESC
        """

        cursor.execute(query)
        resources = cursor.fetchall()

        return {
            "status": "success",
            "total": len(resources),
            "resources": resources
        }, 200

    except Exception:
        return {"status": "error", "message": "Could not load resources"}, 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


# 3. Update resource status
@resource_bp.route(
    "/api/resources/<int:resource_id>/status",
    methods=["PUT"]
)
@jwt_required()
def update_resource_status(resource_id):
    data = request.get_json(silent=True)

    if not data or "status" not in data:
        return {"status": "error", "message": "Status is required"}, 400

    allowed_statuses = [
        "AVAILABLE", "ASSIGNED", "ON_THE_WAY",
        "ARRIVED", "BUSY", "MAINTENANCE", "OFFLINE"
    ]

    new_status = str(data["status"]).upper()

    if new_status not in allowed_statuses:
        return {"status": "error", "message": "Invalid resource status"}, 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            "SELECT id FROM resources WHERE id = %s",
            (resource_id,)
        )

        if cursor.fetchone() is None:
            return {"status": "error", "message": "Resource not found"}, 404

        cursor.execute(
            "UPDATE resources SET status = %s WHERE id = %s",
            (new_status, resource_id)
        )

        connection.commit()

        return {
            "status": "success",
            "message": "Resource status updated successfully",
            "resource_id": resource_id,
            "new_status": new_status
        }, 200

    except Exception:
        if connection:
            connection.rollback()
        return {
            "status": "error",
            "message": "Could not update resource status"
        }, 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
