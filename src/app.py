import os
import json
import time
from datetime import datetime, timezone
import flask
from flask import Flask, Response
import psycopg2

app = Flask(__name__)

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', '127.0.0.1'),
        port=os.getenv('POSTGRES_PORT', '5432'),
        dbname=os.getenv('POSTGRES_DB', 'dockerdb'),
        user=os.getenv('POSTGRES_USER', 'docker'),
        password=os.getenv('POSTGRES_PASSWORD', '')
    )


@app.route('/')
def index():
    status = {
        'status': 'ok',
        'python_version': os.popen('python --version').read().strip(),
        'timestamp': datetime.now(timezone.utc).isoformat(),
    }
    html = f"""<!DOCTYPE html>
<html>
<head><title>Python Status</title></head>
<body>
<h1>Python Status</h1>
<ul>
"""
    for key, value in status.items():
        html += f"<li><strong>{key}:</strong> {value}</li>\n"
    html += "</ul>\n</body>\n</html>\n"
    return Response(html, mimetype='text/html')


@app.route('/health')
def health():
    return Response("OK", mimetype='text/plain')


@app.route('/database')
def database():
    try:
        conn = get_db_connection()
        status = conn.info.status
        conn.close()
        return Response(
            f"Connected to '{os.getenv('POSTGRES_DB')}' on '{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}'.",
            mimetype='text/plain'
        )
    except Exception as e:
        return Response(f"Error: Unable to connect to '{os.getenv('POSTGRES_DB')}' on '{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}'.", status=500)


@app.route('/metrics')
def metrics():
    metrics_data = {
        'status': 'ok',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'database': None
    }

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT pg_database_size(%s) as size, (SELECT COUNT(*) FROM pg_stat_activity WHERE datname = %s) as connections", (os.getenv('POSTGRES_DB'), os.getenv('POSTGRES_DB')))
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if row:
            metrics_data['database'] = {
                'connected': True,
                'size_bytes': row[0],
                'size_human': f"{round(row[0] / 1024 / 1024, 2)} MB",
                'connections': row[1]
            }
    except Exception:
        metrics_data['database'] = {'connected': False}

    return Response(json.dumps(metrics_data, indent=2), mimetype='application/json')


@app.route('/flask')
def flask_info():
    return Response(
        json.dumps({
            'flask': 'working',
            'version': flask.__version__,
            'python_version': os.popen('python --version').read().strip(),
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }, indent=2),
        mimetype='application/json'
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)