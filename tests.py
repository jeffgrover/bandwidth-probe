import unittest
import sqlite3
import json
from datetime import datetime, timedelta
import os
import pandas as pd
import logging
import sys
from speedtest_collector import setup_database, run_speedtest, save_result
from app import app, get_db_connection

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('test_debug.log')
    ]
)
logger = logging.getLogger(__name__)

class BandwidthProbeTests(unittest.TestCase):
    """Test suite for both collector and web interface"""
    
    def setUp(self):
        """Set up test fixtures before each test method"""
        logger.info("Setting up test environment")
        
        # Create test database
        self.test_db = 'test_speedtest.db'
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        logger.debug("Created clean test database at %s", self.test_db)
        
        # Set up test client
        app.config['TESTING'] = True
        app.config['DATABASE'] = self.test_db
        self.client = app.test_client()
        logger.debug("Flask test client configured")
        
        # Initialize database
        setup_database(self.test_db)
        logger.debug("Database initialized")
    
    def tearDown(self):
        """Clean up after each test method"""
        logger.info("Cleaning up test environment")
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
            logger.debug("Removed test database")
    
    def test_database_setup(self):
        """Test database initialization"""
        print("Starting database setup test")
        logger.info("Running database setup test")
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        
        # Verify table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='speedtests'")
        self.assertIsNotNone(cursor.fetchone())
        logger.debug("Verified speedtests table exists")
        
        # Verify schema
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='speedtests'")
        schema = cursor.fetchone()[0]
        self.assertIn('timestamp TEXT', schema)
        self.assertIn('download REAL', schema)
        self.assertIn('upload REAL', schema)
        self.assertIn('ping REAL', schema)
        self.assertIn('error TEXT', schema)
        logger.debug("Verified table schema")
        
        conn.close()
    
    def test_save_result(self):
        """Test saving speedtest results"""
        logger.info("Running save result test")
        
        # Test successful result
        test_data = {
            'download': 100.0,
            'upload': 50.0,
            'ping': 20.0,
            'error': None
        }
        save_result(test_data, self.test_db)
        logger.debug("Saved successful test result")
        
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM speedtests ORDER BY timestamp DESC LIMIT 1')
        row = cursor.fetchone()
        conn.close()
        
        self.assertIsNotNone(row)
        self.assertEqual(row[1], 100.0)  # download
        self.assertEqual(row[2], 50.0)   # upload
        self.assertEqual(row[3], 20.0)   # ping
        self.assertIsNone(row[4])        # error
        logger.debug("Verified successful result was saved correctly")
    
    def test_web_interface(self):
        """Test web interface with empty database"""
        logger.info("Running web interface test")
        
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Total tests:', response.data)
        logger.debug("Verified web interface response")

if __name__ == '__main__':
    unittest.main(verbosity=2)
