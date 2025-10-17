# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

A Python/Flask web application that monitors Canyon Lake (Texas) water levels using real-time USGS data. Displays current status, historical trends, and Guadalupe River flow rates with visual indicators and interactive charts.

## Commands

### Development & Running

```bash
# Setup virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
# Access at: http://localhost:8081

# Test data fetching standalone
python canyon_lake_data.py
```

### Testing the API Endpoints

```bash
# Current status
curl http://localhost:8081/api/status

# Historical data (30 days)
curl http://localhost:8081/api/history

# River flow data (12-hour intervals)
curl http://localhost:8081/api/flow-12hr
```

## Architecture

### Application Structure

**Flask App (app.py)**
- Simple REST API server with three routes:
  - `/` - Main status page (index.html)
  - `/chart` - Historical charts page (chart.html)
  - `/api/status` - Current lake status JSON
  - `/api/history` - 30-day historical data JSON
  - `/api/flow-12hr` - Guadalupe River flow data JSON
- Runs on port 8081, accessible from all interfaces (0.0.0.0)

**Data Layer (canyon_lake_data.py)**
- `CanyonLakeMonitor` class handles all USGS API interactions
- Fetches and parses water level and river flow data
- Calculates lake fullness percentage and status categories

**Frontend (templates/ and static/)**
- HTML templates with JavaScript for dynamic updates
- Auto-refresh functionality (typically every 5 minutes)
- Animated water level visualizations
- Chart.js for historical data visualization

### USGS Data Integration

**Primary Data Sources:**
- **Lake Elevation**: Site 08167700 (Canyon Lake near New Braunfels, TX)
  - Parameter: 62614 (Lake surface elevation above NGVD 1929)
  - Current values API: `https://waterservices.usgs.gov/nwis/iv/`
  - Daily values API: `https://waterservices.usgs.gov/nwis/dv/`

- **River Flow**: Site 08167500 (Guadalupe River near Spring Branch, TX)
  - Parameter: 00060 (Streamflow in cubic feet per second)
  - Used for historical flow analysis

**Key Elevation Values:**
- Conservation pool: 909.0 ft (considered "100% full")
- Flood pool: 943.0 ft (flood stage)
- Empty elevation: 860.0 ft (approximation for percentage calculations)
- Conservation capacity: 378,781 acre-feet

**Status Categories:**
- **Flood** (red): elevation >= 943 ft
- **Full** (blue): elevation >= 909 ft
- **Excellent** (blue): 90-100% full
- **Good** (green): 75-90% full
- **Low** (orange): <75% full

### Data Flow

1. Frontend JavaScript calls Flask API endpoints
2. Flask routes invoke `CanyonLakeMonitor` methods
3. Monitor class fetches data from USGS REST APIs
4. Data is parsed, calculated, and formatted as JSON
5. Frontend receives JSON and updates UI/charts

### Historical Data Processing

- **Lake Data**: Fetches daily elevation values over specified period
- **River Flow**: Fetches instantaneous values, aggregates into 12-hour periods
- **Aggregation**: Groups flow measurements by 12-hour blocks (00:00-12:00, 12:00-24:00)
- **Combined Output**: Merges lake and river data by date for comprehensive view

## Error Handling

The application handles several error conditions gracefully:
- USGS API unavailable or unreachable
- Malformed API responses
- Missing data points in time series
- Network timeouts and HTTP errors

Error responses return JSON with `status: 'error'` and descriptive `message` field.

## Important Implementation Details

- **No Database**: All data is fetched in real-time from USGS APIs
- **No Caching**: Each API call results in fresh USGS data fetch (consider adding caching for production)
- **Percentage Calculation**: Linear interpolation between empty (860 ft) and conservation pool (909 ft)
- **Debug Mode**: Currently set to `debug=False` in app.py
- **Port Configuration**: Runs on port 8081 (not the default Flask 5000)
- **12-Hour Flow Aggregation**: Averages instantaneous measurements within each 12-hour window
