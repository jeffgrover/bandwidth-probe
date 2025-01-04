# Bandwidth Probe

A system for monitoring and visualizing internet bandwidth over time. It performs speed tests at regular intervals and provides a web interface to view the results.

## Features

- Runs speedtest every 5 minutes on the clock (1:00, 1:05, 1:10, etc.)
- Stores results in a SQLite database
- Web interface showing:
  - Min/Max/Average download and upload speeds
  - Time series graph of bandwidth measurements
  - Error tracking
  - Test statistics for the last 24 hours

## Requirements

- Python 3.x
- speedtest-cli
- Flask
- pandas
- plotly

## Installation

All dependencies are automatically installed in the virtual environment. To set up:

1. Activate the virtual environment:
   ```bash
   source venv/bin/activate
   ```

## Usage

1. Start the data collector in one terminal:
   ```bash
   python speedtest_collector.py
   ```

2. Start the web interface in another terminal:
   ```bash
   python app.py
   ```

3. Open your web browser and visit:
   ```
   http://localhost:5000
   ```

The web interface will automatically refresh every 5 minutes to show the latest data.

## Data Storage

All speed test results are stored in `speedtest.db` using SQLite. The database is automatically created when the collector is first run.

## Error Handling

- The collector will automatically retry on the next 5-minute interval if a test fails
- All errors are logged to the database and displayed in the web interface
- The system will continue running indefinitely until manually stopped

## Stopping the System

To stop either component:
1. Press Ctrl+C in the respective terminal
2. Deactivate the virtual environment when done:
   ```bash
   deactivate
