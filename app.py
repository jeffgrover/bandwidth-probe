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

def get_stats(conn, offset_days=0):
    """Calculate statistics for the dashboard"""
    cursor = conn.cursor()
    
    # Get 24 hours of data based on offset
    end_date = datetime.now() - timedelta(days=offset_days)
    start_date = end_date - timedelta(days=1)
    
    # Calculate period-specific stats for successful tests
    cursor.execute('''
        SELECT 
            MIN(download) as min_down,
            MAX(download) as max_down,
            AVG(download) as avg_down,
            MIN(upload) as min_up,
            MAX(upload) as max_up,
            AVG(upload) as avg_up,
            COUNT(*) as test_count
        FROM speedtests
        WHERE error IS NULL
        AND timestamp > ?
        AND timestamp <= ?
    ''', (start_date.isoformat(), end_date.isoformat()))
    period_stats = cursor.fetchone()
    
    # Get period error count and total tests
    cursor.execute('''
        SELECT 
            SUM(CASE WHEN error IS NOT NULL THEN 1 ELSE 0 END) as error_count,
            COUNT(*) as total_count
        FROM speedtests
        WHERE timestamp > ?
        AND timestamp <= ?
    ''', (start_date.isoformat(), end_date.isoformat()))
    period_row = cursor.fetchone()
    period_errors = period_row[0] if period_row[0] is not None else 0
    period_total = period_row[1] if period_row[1] is not None else 0
    
    # Calculate overall stats for successful tests
    cursor.execute('''
        SELECT 
            MIN(download) as min_down,
            MAX(download) as max_down,
            AVG(download) as avg_down,
            MIN(upload) as min_up,
            MAX(upload) as max_up,
            AVG(upload) as avg_up,
            COUNT(*) as test_count
        FROM speedtests
        WHERE error IS NULL
    ''')
    overall_stats = cursor.fetchone()
    
    # Get overall error count and total tests
    cursor.execute('''
        SELECT 
            SUM(CASE WHEN error IS NOT NULL THEN 1 ELSE 0 END) as error_count,
            COUNT(*) as total_count
        FROM speedtests
    ''')
    overall_row = cursor.fetchone()
    overall_errors = overall_row[0] if overall_row[0] is not None else 0
    overall_total = overall_row[1] if overall_row[1] is not None else 0
    
    # Structure the stats data
    stats = {
        'period': {
            'download': {
                'min': period_stats[0] if period_stats[0] is not None else 0,
                'max': period_stats[1] if period_stats[1] is not None else 0,
                'avg': period_stats[2] if period_stats[2] is not None else 0
            },
            'upload': {
                'min': period_stats[3] if period_stats[3] is not None else 0,
                'max': period_stats[4] if period_stats[4] is not None else 0,
                'avg': period_stats[5] if period_stats[5] is not None else 0
            },
            'test_count': period_stats[6] if period_stats[6] is not None else 0,
            'error_count': period_errors,
            'error_chart': {
                'data': [{
                    'type': 'pie',
                    'values': [period_total - period_errors, period_errors],
                    'labels': ['Success', 'Failure'],
                    'hole': 0.4,
                    'marker': {'colors': ['#2ecc71', '#e74c3c']}
                }],
                'layout': {
                    'showlegend': False,
                    'margin': {'t': 0, 'b': 0, 'l': 0, 'r': 0},
                    'height': 150,
                    'width': 300
                }
            },
            'distribution': get_distribution_data(cursor, 'period', start_date.isoformat(), end_date.isoformat())
        },
        'overall': {
            'download': {
                'min': overall_stats[0] if overall_stats[0] is not None else 0,
                'max': overall_stats[1] if overall_stats[1] is not None else 0,
                'avg': overall_stats[2] if overall_stats[2] is not None else 0
            },
            'upload': {
                'min': overall_stats[3] if overall_stats[3] is not None else 0,
                'max': overall_stats[4] if overall_stats[4] is not None else 0,
                'avg': overall_stats[5] if overall_stats[5] is not None else 0
            },
            'test_count': overall_stats[6] if overall_stats[6] is not None else 0,
            'error_count': overall_errors,
            'error_chart': {
                'data': [{
                    'type': 'pie',
                    'values': [overall_total - overall_errors, overall_errors],
                    'labels': ['Success', 'Failure'],
                    'hole': 0.4,
                    'marker': {'colors': ['#2ecc71', '#e74c3c']}
                }],
                'layout': {
                    'showlegend': False,
                    'margin': {'t': 0, 'b': 0, 'l': 0, 'r': 0},
                    'height': 150,
                    'width': 300
                }
            },
            'distribution': get_distribution_data(cursor, 'overall')
        }
    }
    return stats

def get_distribution_data(cursor, period_type, start_date=None, end_date=None):
    """Generate distribution data for download and upload speeds"""
    if period_type == 'period':
        cursor.execute('''
            SELECT download, upload
            FROM speedtests
            WHERE error IS NULL
            AND timestamp > ?
            AND timestamp <= ?
            ORDER BY timestamp
        ''', (start_date, end_date))
    else:  # overall
        cursor.execute('''
            SELECT download, upload
            FROM speedtests
            WHERE error IS NULL
            ORDER BY timestamp
        ''')
    
    rows = cursor.fetchall()
    if not rows:
        return None
    
    downloads = [row[0] for row in rows]
    uploads = [row[1] for row in rows]
    
    return {
        'download': {
            'data': [{
                'type': 'violin',
                'y': downloads,
                'name': 'Download',
                'box': {'visible': True},
                'line': {'color': '#3498db'},
                'meanline': {'visible': True}
            }],
            'layout': {
                'showlegend': False,
                'margin': {'t': 0, 'b': 0, 'l': 30, 'r': 0},
                'height': 100,
                'yaxis': {'title': ''}
            }
        },
        'upload': {
            'data': [{
                'type': 'violin',
                'y': uploads,
                'name': 'Upload',
                'box': {'visible': True},
                'line': {'color': '#2ecc71'},
                'meanline': {'visible': True}
            }],
            'layout': {
                'showlegend': False,
                'margin': {'t': 0, 'b': 0, 'l': 30, 'r': 0},
                'height': 100,
                'yaxis': {'title': ''}
            }
        }
    }

def get_plot_data(conn, offset_days=0):
    """Generate plot data for the dashboard"""
    cursor = conn.cursor()
    
    # Get 24 hours of data based on offset
    end_date = datetime.now() - timedelta(days=offset_days)
    start_date = end_date - timedelta(days=1)
    
    cursor.execute('''
        SELECT timestamp, download, upload
        FROM speedtests
        WHERE error IS NULL 
        AND timestamp > ? 
        AND timestamp <= ?
        ORDER BY timestamp
    ''', (start_date.isoformat(), end_date.isoformat()))
    
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
    
    # Format date range for title
    start_str = start_date.strftime('%Y-%m-%d %H:%M')
    end_str = end_date.strftime('%Y-%m-%d %H:%M')
    title = f'Bandwidth for {start_str} to {end_str}'
    
    layout = {
        'title': title,
        'xaxis': {'title': 'Time'},
        'yaxis': {'title': 'Speed (Mbps)'}
    }
    
    return {'data': data, 'layout': layout}

@app.route('/')
@app.route('/<int:offset>')
def index(offset=0):
    logger.info(f"Received request for index page with offset {offset}")
    conn = get_db_connection()
    if conn is None:
        return 'Database not found. Please start the collector first.', 503
    
    try:
        # Get the earliest timestamp to determine max offset
        cursor = conn.cursor()
        cursor.execute('SELECT MIN(timestamp) FROM speedtests WHERE error IS NULL')
        earliest_timestamp = cursor.fetchone()[0]
        max_offset = 0
        
        if earliest_timestamp:
            earliest_date = datetime.fromisoformat(earliest_timestamp)
            max_offset = (datetime.now() - earliest_date).days
        
        stats = get_stats(conn, offset)
        plot_data = get_plot_data(conn, offset)
        
        return render_template('index.html',
                             stats=stats,
                             plot_data=plot_data,
                             now=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                             current_offset=offset,
                             max_offset=max_offset)
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
            port=8000,
            debug=True,
            use_reloader=False
        )
    except Exception as e:
        logger.error("Failed to start Flask: %s", str(e))
        sys.exit(1)
