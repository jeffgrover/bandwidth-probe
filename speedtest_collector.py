import json
import sqlite3
import subprocess
import time
from datetime import datetime
import sys
import logging
import os

# Configure logging with both file and console output
def setup_logging():
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=logging.DEBUG,
        format=log_format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('speedtest.log')
        ]
    )

# Get the directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, 'speedtest.db')

def verify_speedtest_cli():
    """Verify speedtest is installed and accessible"""
    try:
        # Run with --accept-license to avoid interactive prompt
        result = subprocess.run(['speedtest', '--accept-license', '--json'], 
                              capture_output=True, 
                              text=True)
        if result.returncode == 0:
            logging.info("Speedtest verified successfully")
            return True
        else:
            logging.error("Speedtest check failed: %s", result.stderr)
            return False
    except FileNotFoundError:
        logging.error("Speedtest not found. Please install it first.")
        return False

def setup_database(db_path=DB_PATH):
    """Initialize the database with the required schema"""
    logging.info("Setting up database at %s", db_path)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS speedtests
                 (timestamp TEXT, download REAL, upload REAL, ping REAL, error TEXT)''')
    conn.commit()
    conn.close()

def run_speedtest():
    try:
        # First run to accept license if needed
        subprocess.run(['speedtest', '--accept-license'], 
                      capture_output=True, 
                      text=True)
        
        # Actual test run
        result = subprocess.run(['speedtest', '--json'], 
                              capture_output=True, 
                              text=True)
        
        if result.returncode == 0:
            # Log raw output for debugging
            logging.debug("Raw speedtest output: %s", result.stdout)
            data = json.loads(result.stdout)
            return {
                'download': data['download'] / 1_000_000,  # Convert to Mbps (bits/s to Mbps)
                'upload': data['upload'] / 1_000_000,      # Convert to Mbps (bits/s to Mbps)
                'ping': data['ping'],
                'error': None
            }
        else:
            logging.error("Speedtest stderr: %s", result.stderr)
            return {'error': result.stderr}
    except Exception as e:
        logging.error("Error running speedtest: %s", str(e))
        if 'result' in locals():
            logging.error("Stdout: %s", result.stdout)
            logging.error("Stderr: %s", result.stderr)
        return {'error': str(e)}

def save_result(data, db_path=DB_PATH):
    """Save speedtest result to database"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    timestamp = datetime.now().isoformat()
    
    if 'error' in data and data['error']:
        c.execute('INSERT INTO speedtests VALUES (?, ?, ?, ?, ?)',
                 (timestamp, None, None, None, data['error']))
    else:
        c.execute('INSERT INTO speedtests VALUES (?, ?, ?, ?, ?)',
                 (timestamp, data['download'], data['upload'], data['ping'], None))
    
    conn.commit()
    conn.close()

def wait_until_next_interval(interval_minutes=15):
    current_time = datetime.now()
    minutes = current_time.minute
    next_interval = ((minutes // interval_minutes) + 1) * interval_minutes
    if next_interval == 60:
        next_interval = 0
    
    target_time = current_time.replace(minute=next_interval, second=0, microsecond=0)
    if target_time <= current_time:
        target_time = target_time.replace(hour=target_time.hour + 1)
    
    sleep_seconds = (target_time - current_time).total_seconds()
    time.sleep(sleep_seconds)

def main():
    setup_logging()
    logging.info("Starting bandwidth probe collector...")
    
    # Verify dependencies
    if not verify_speedtest_cli():
        logging.error("speedtest-cli verification failed")
        sys.exit(1)
    
    # Initialize database
    try:
        setup_database()
        logging.info("Database initialized successfully")
    except Exception as e:
        logging.error("Failed to initialize database: %s", str(e))
        sys.exit(1)
    
    logging.info("Starting speedtest collection (every 15 minutes)...")
    while True:
        try:
            result = run_speedtest()
            save_result(result)
            
            if result.get('error'):
                logging.error("Speedtest error: %s", result['error'])
            else:
                logging.info("Speedtest completed - Down: %.2f Mbps, Up: %.2f Mbps, Ping: %.1f ms",
                           result['download'], result['upload'], result['ping'])
            
            wait_until_next_interval()
        except KeyboardInterrupt:
            logging.info("Exiting...")
            sys.exit(0)
        except Exception as e:
            logging.error("Unexpected error: %s", e)
            time.sleep(300)  # Wait 5 minutes on error

if __name__ == '__main__':
    main()
