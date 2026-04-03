"""
LightTuner UI Server
Flask-based backend providing RESTful APIs for the LightTuner dashboard.
Handles experiment tracking, test status, and metric visualization data.
"""
import argparse
import os
import sys
from datetime import datetime
from typing import Any
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from light_tuner.utils.logger import logger
from light_tuner.storage.sqlite_manager import SQLiteManager
import json
from pathlib import Path

# Setup paths for Flask to find the Vue.js build artifacts
root_path = os.path.dirname(os.path.abspath(__file__))
template_folder = os.path.join(root_path, "templates")
static_folder = os.path.join(root_path, "static")

# Initialize Flask App
app = Flask(
    __name__,
    template_folder=template_folder,
    static_folder=static_folder,
    static_url_path="/static"  # Matches the 'base' config in Vue/Vite builds
)

# Enable Cross-Origin Resource Sharing (CORS) for development
CORS(app, resources=r"/*")


# -------------------------- Response Helpers --------------------------
def success_response(data: Any = None, msg: str = "Operation successful"):
    """Standard success response format"""
    return jsonify({
        "code": 200,
        "msg": msg,
        "data": data
    })


def error_response(msg: str = "Operation failed", code: int = 500):
    """Standard error response format"""
    return jsonify({
        "code": code,
        "msg": msg,
        "data": None
    })


def parse_datetime(date_str: str) -> datetime:
    """Parses a date string into a datetime object"""
    return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")


# -------------------------- Experiment API --------------------------

@app.route("/api/experiment", methods=["GET"])
def get_experiments():
    """Retrieves experiment records with optional filters and sorting."""
    try:
        # 1. Extract optional query filters
        name = request.args.get("name")
        status = request.args.get("status")
        search_mode = request.args.get("search_mode")

        # 2. Extract sorting parameters with sensible defaults
        sort_by = request.args.get("sort_by", "start_time")
        sort_order = request.args.get("sort_order", "DESC")

        # 3. Query the database
        experiments = db_manager.select_experiments(
            name=name,
            status=status,
            search_mode=search_mode,
            sort_by=sort_by,
            sort_order=sort_order
        )

        return success_response(
            data=experiments,
            msg=f"Found {len(experiments)} records"
        )

    except Exception as e:
        logger.error(f"Experiment query error: {str(e)}")
        return error_response(f"Internal Server Error: {str(e)}")


# -------------------------- Test API --------------------------

@app.route("/api/test", methods=["GET"])
def get_tests():
    """Retrieves all test records associated with a specific experiment ID."""
    experiment_id = request.args.get("experiment_id")
    if not experiment_id:
        return error_response("Missing required parameter: experiment_id", code=400)

    try:
        tests = db_manager.select_test_by_experiment_id(experiment_id)
        return success_response(
            data=tests,
            msg=f"Found {len(tests)} test records"
        )
    except Exception as e:
        logger.error(f"Test query error: {str(e)}")
        return error_response(f"Internal Server Error: {str(e)}")


# -------------------------- Metrics API --------------------------

@app.route("/api/metrics", methods=["GET"])
def get_metrics():
    """Retrieves metrics for a list of test IDs (supports batch comparison)."""
    # 1. Get comma-separated IDs (e.g., "1,2,3")
    test_id_list_str = request.args.get("test_id_list")
    if not test_id_list_str:
        return error_response("Missing required parameter: test_id_list", code=400)

    try:
        # 2. Parse string into a list of integers
        try:
            test_id_list = [int(tid.strip()) for tid in test_id_list_str.split(",") if tid.strip()]
        except ValueError:
            return error_response("Invalid format: test_id_list must be comma-separated integers", code=400)

        if not test_id_list:
            return error_response("test_id_list cannot be empty", code=400)

        # 3. Get optional filters
        metric_name = request.args.get("metric_name")
        tag = request.args.get("tag")
        data_type = request.args.get("data_type")

        # 4. Fetch metrics from DB
        metrics = db_manager.select_metrics(
            test_id_list=test_id_list,
            metric_name=metric_name,
            tag=tag,
            data_type=data_type
        )

        # 5. Deserialize JSON fields for frontend consumption
        for m in metrics:
            if m.get('data_type') in ['matrix', 'array', 'json']:
                try:
                    m['metric_val'] = json.loads(m['metric_val'])
                except Exception:
                    pass

        return success_response(
            data=metrics,
            msg=f"Retrieved {len(metrics)} metrics from {len(test_id_list)} tests"
        )

    except Exception as e:
        logger.error(f"Metric query exception: {str(e)}")
        return error_response(f"Internal Server Error: {str(e)}")


# -------------------------- Static Assets & SPA Routing --------------------------

@app.route("/")
def index():
    """Serves the Vue entry file (index.html)."""
    try:
        return render_template("index.html")
    except Exception:
        return "<h1>LightTuner UI</h1><p>Frontend assets not found. Ensure templates/index.html exists.</p>", 404


@app.route("/<path:path>")
def static_proxy(path):
    """Proxies requests for other static assets (SVG, ICO, CSS, JS)."""
    return send_from_directory(app.static_folder, path)


@app.errorhandler(404)
def catch_all(e):
    """Handles Vue Router History mode by redirecting non-API 404s to index.html."""
    if request.path.startswith("/api/"):
        return error_response("API Endpoint not found", code=404)
    return render_template("index.html")


# -------------------------- Service Entry --------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LightTuner UI Server")
    parser.add_argument(
        "--db_dir",
        required=True,
        help="Directory containing the light_tuner.db file"
    )
    args = parser.parse_args()

    try:
        db_path = str(os.path.abspath(Path(args.db_dir) / "light_tuner.db"))
        db_manager = SQLiteManager(db_path)

        logger.info(f"🚀 LightTuner UI starting. DB Path: {db_path}")

        # Start Flask development server
        app.run(
            host="0.0.0.0",
            port=8080,
            debug=False
        )
    except Exception as e:
        logger.error(f"❌ Failed to start service: {e}")
        sys.exit(1)