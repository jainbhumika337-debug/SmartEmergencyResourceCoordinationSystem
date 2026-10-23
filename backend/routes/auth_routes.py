
from flask import Blueprint, request
from database import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import re

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True)

    if not data:
        return {"status": "error", "message": "JSON data is required"}, 400

    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password", "")
    phone = str(data.get("phone", "")).strip() or None

    if not name or not email or not isinstance(password, str):
        return {
            "status": "error",
            "message": "Name, email and password are required"
        }, 400

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return {"status": "error", "message": "Enter a valid email"}, 400

    if len(password) < 8:
        return {
            "status": "error",
            "message": "Password must be at least 8 characters"
        }, 400

    if len(name) > 100 or len(email) > 150:
        return {"status": "error", "message": "Name or email is too long"}, 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return {
                "status": "error",
                "message": "An account with this email already exists"
            }, 409

        password_hash = generate_password_hash(password)

        cursor.execute(
            """
            INSERT INTO users (name, email, password_hash, role, phone)
            VALUES (%s, %s, %s, 'OPERATOR', %s)
            """,
            (name, email, password_hash, phone)
        )
        connection.commit()
        user_id = cursor.lastrowid

        return {
            "status": "success",
            "message": "Registration successful",
            "user": {
                "id": user_id,
                "name": name,
                "email": email,
                "role": "OPERATOR"
            }
        }, 201

    except Exception as e:
        if connection:
            connection.rollback()
        return {"status": "error", "message": str(e)}, 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)

    if not data:
        return {"status": "error", "message": "JSON data is required"}, 400

    email = str(data.get("email", "")).strip().lower()
    password = data.get("password", "")

    if not email or not isinstance(password, str) or not password:
        return {
            "status": "error",
            "message": "Email and password are required"
        }, 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, name, email, password_hash, role
            FROM users
            WHERE email = %s
            """,
            (email,)
        )
        user = cursor.fetchone()

        if not user or not check_password_hash(user["password_hash"], password):
            return {
                "status": "error",
                "message": "Invalid email or password"
            }, 401

        token = create_access_token(
            identity=str(user["id"]),
            additional_claims={"role": user["role"]}
        )

        return {
            "status": "success",
            "message": "Login successful",
            "access_token": token,
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "role": user["role"]
            }
        }, 200

    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def current_user():
    user_id = get_jwt_identity()
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT id, name, email, role, phone FROM users WHERE id = %s",
            (user_id,)
        )
        user = cursor.fetchone()

        if not user:
            return {"status": "error", "message": "User not found"}, 404

        return {"status": "success", "user": user}, 200

    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
