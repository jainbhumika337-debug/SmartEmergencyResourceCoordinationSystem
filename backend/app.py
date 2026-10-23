import os

from dotenv import load_dotenv
load_dotenv()
from flask import Flask
from flask_cors import CORS
from database import get_db_connection
from routes.emergency_routes import emergency_bp
from routes.resource_routes import resource_bp
from services.matching_service import find_best_resources
from flask_jwt_extended import JWTManager, jwt_required
from routes.auth_routes import auth_bp

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
jwt = JWTManager(app)

CORS(app)

app.register_blueprint(emergency_bp)
app.register_blueprint(resource_bp)
app.register_blueprint(auth_bp)

@app.route("/")
def home():
    return {
        "message": "Smart Emergency Resource Coordination System API is running!",
        "status": "success"
    }

@app.route("/api/health")
def health():
    return {
        "system": "Smart Emergency Resource Coordination System",
        "status": "healthy"
    }

@app.route("/api/db-test")
def database_test():
    try:
        connection = get_db_connection()

        cursor = connection.cursor()
        cursor.execute("SELECT DATABASE()")

        database_name = cursor.fetchone()[0]

        cursor.close()
        connection.close()

        return {
            "status": "success",
            "database": database_name,
            "message": "MySQL database connected successfully!"
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }, 500

@app.route("/api/emergencies/<int:emergency_id>/match", methods=["GET"])
@jwt_required()
def match_resources(emergency_id):
    result, status_code = find_best_resources(emergency_id)
    return result, status_code


if __name__ == "__main__":
    app.run(debug=False)