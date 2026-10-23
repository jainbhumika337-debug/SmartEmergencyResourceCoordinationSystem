
import math
from database import get_db_connection


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two locations in kilometers.
    Uses the Haversine formula.
    """
    earth_radius = 6371

    lat1 = math.radians(float(lat1))
    lon1 = math.radians(float(lon1))
    lat2 = math.radians(float(lat2))
    lon2 = math.radians(float(lon2))

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return earth_radius * c


def find_best_resources(emergency_id):
    """
    Find available resources and rank them
    according to their distance from an emergency.
    """
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, emergency_code, latitude, longitude,
                   emergency_type, severity
            FROM emergencies
            WHERE id = %s
            """,
            (emergency_id,)
        )

        emergency = cursor.fetchone()

        if not emergency:
            return {
                "status": "error",
                "message": "Emergency not found"
            }, 404

        cursor.execute(
            """
            SELECT
                r.id,
                r.resource_name,
                r.capacity,
                r.latitude,
                r.longitude,
                r.status,
                rt.type_name AS resource_type
            FROM resources r
            JOIN resource_types rt
                ON r.resource_type_id = rt.id
            WHERE r.status = 'AVAILABLE'
              AND r.latitude IS NOT NULL
              AND r.longitude IS NOT NULL
            """
        )

        resources = cursor.fetchall()

        ranked_resources = []

        for resource in resources:
            distance = calculate_distance(
                emergency["latitude"],
                emergency["longitude"],
                resource["latitude"],
                resource["longitude"]
            )

            ranked_resources.append({
                "resource_id": resource["id"],
                "resource_name": resource["resource_name"],
                "resource_type": resource["resource_type"],
                "capacity": resource["capacity"],
                "status": resource["status"],
                "distance_km": round(distance, 2)
            })

        ranked_resources.sort(key=lambda item: item["distance_km"])

        return {
            "status": "success",
            "emergency_id": emergency["id"],
            "emergency_code": emergency["emergency_code"],
            "total_available_resources": len(ranked_resources),
            "recommended_resources": ranked_resources
        }, 200

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }, 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()
