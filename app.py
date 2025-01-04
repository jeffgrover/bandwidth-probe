from flask import Flask, jsonify, render_template
import sqlite3
import logging
import sys
import os
from datetime import datetime, timedelta
import plotly.graph_objs as go
import json

# Configure logging to output to both file and console
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('flask_debug.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Get the directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, 'speedtest.db')

# Create Flask app
app = Flask(__name__)

def get_db_connection():
    """Create a database connection"""
    try:
        # Use test database if configured
        db_path = app.config.get('DATABASE', DB_PATH)
        if not os.path.exists(db_path):
            logger.warning("Database does not exist at %s", db_path)
            return None
        conn = sqlite3.connect(db_path)
        logger.debug("Database connection established to %s", db_path)
        return conn
    except Exception as e:
        logger.error("Database connection failed: %s", str(e))
        return None

def get_stats(conn):
    """Calculate statistics for the dashboard"""
    cursor = conn.cursor()
    
    # Get last 24 hours of data
    yesterday = (datetime.now() - timedelta(days=1)).isoformat()
    
    # Calculate min/max/avg for download and upload
    cursor.execute('''
        SELECT 
            MIN(download) as min_down,
            MAX(download) as max_down,
            AVG(download) as avg_down,
            MIN(upload) as min_up,
            MAX(upload) as max_up,
            AVG(upload) as avg_up
        FROM speedtests
        WHERE error IS NULL
    ''')
    row = cursor.fetchone()
    
    # Count tests and errors in last 24h
    cursor.execute('SELECT COUNT(*) FROM speedtests WHERE timestamp > ?', (yesterday,))
    last_24h_tests = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM speedtests WHERE error IS NOT NULL')
    error_count = cursor.fetchone()[0]
    
    return {
        'download': {
            'min': row[0] if row[0] else 0,
            'max': row[1] if row[1] else 0,
            'avg': row[2] if row[2] else 0
        },
        'upload': {
            'min': row[3] if row[3] else 0,
            'max': row[4] if row[4] else 0,
            'avg': row[5] if row[5] else 0
        },
        'last_24h_tests': last_24h_tests,
        'error_count': error_count
    }

def get_plot_data(conn):
    """Generate plot data for the dashboard"""
    cursor = conn.cursor()
    
    # Get last 24 hours of data
    yesterday = (datetime.now() - timedelta(days=1)).isoformat()
    cursor.execute('''
        SELECT timestamp, download, upload
        FROM speedtests
        WHERE error IS NULL AND timestamp > ?
        ORDER BY timestamp
    ''', (yesterday,))
    
    rows = cursor.fetchall()
    if not rows:
        return None
        
    timestamps = [row[0] for row in rows]
    downloads = [row[1] for row in rows]
    uploads = [row[2] for row in rows]
    
    data = [
        {
            'type': 'scatter',
            'x': timestamps,
            'y': downloads,
            'name': 'Download',
            'line': {'color': '#3498db'}
        },
        {
            'type': 'scatter',
            'x': timestamps,
            'y': uploads,
            'name': 'Upload',
            'line': {'color': '#2ecc71'}
        }
    ]
    
    layout = {
        'title': 'Bandwidth Over Time',
        'xaxis': {'title': 'Time'},
        'yaxis': {'title': 'Speed (Mbps)'}
    }
    
    return {'data': data, 'layout': layout}

@app.route('/')
def index():
    logger.info("Received request for index page")
    conn = get_db_connection()
    if conn is None:
        return 'Database not found. Please start the collector first.', 503
    
    try:
        stats = get_stats(conn)
        plot_data = get_plot_data(conn)
        
        return render_template('index.html',
                             stats=stats,
                             plot_data=plot_data,
                             now=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    except Exception as e:
        logger.error("Database query failed: %s", str(e))
        return f"Error accessing database: {str(e)}", 500
    finally:
        if conn:
            conn.close()

@app.route('/health')
def health():
    logger.info("Received health check request")
    return 'OK'

if __name__ == '__main__':
    logger.info("Starting Flask application...")
    try:
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True,
            use_reloader=False
        )
    except Exception as e:
        logger.error("Failed to start Flask: %s", str(e))
        sys.exit(1)
