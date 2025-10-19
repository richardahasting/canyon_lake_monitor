# Canyon Lake Water Level Monitor

A comprehensive Python Flask application that displays real-time water level data, historical trends, weather conditions, and visitor analytics for Canyon Lake in Texas.

> **Note**: This Flask development server is used for both development and production deployment.

## Features

### Main Dashboard (/)
- **Real-time water level data** from USGS monitoring station
- **Visual representation** of lake fullness with animated water gauge
- **Color-coded status indicators**:
  - **Flood** (red): Above flood stage (943 ft)
  - **Full** (blue): At conservation capacity (909 ft)
  - **Excellent** (blue): 90-100% full
  - **Good** (green): 75-90% full
  - **Low** (orange): 40-75% full
  - **Critical** (red): Below 40% full
- **Current statistics**:
  - Lake elevation (feet above NGVD 1929)
  - Percentage full
  - Feet below conservation pool
- **Weather information** from National Weather Service (weather.gov API)
  - Current temperature (°F)
  - Weather conditions
- **Astronomical data**:
  - Moon phase with emoji representation
  - Sunrise and sunset times (24-hour format)
  - Automatic day/night theme switching
- **Auto-refresh** every 5 minutes
- **Caribbean blue theme** inspired by Belize ocean colors

### Historical Data (/chart)
- **30-day historical view** of lake levels
- **River flow data** from Guadalupe River near Spring Branch
- **Interactive Chart.js visualizations**:
  - Lake elevation over time
  - Percentage full trends
  - River inflow rates
- Data aggregated in 12-hour increments for river flow

### Analytics Dashboard (/analytics)
- **IP-based access control** (restricted to authorized IPs)
- **Visitor statistics**:
  - Total hits (all time)
  - Unique visitors (all time, 24 hours, 7 days)
  - First and last visit timestamps
- **Page hit breakdown** by route (bar chart)
- **Recent visits table** (last 20 visits with timestamps and IPs)
- **Top visitors** ranking with hit counts and percentages
- **Auto-refresh** every 5 minutes

## Installation

### Prerequisites
- Python 3.7 or higher
- pip package manager

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/richardahasting/canyon_lake_monitor.git
   cd canyon_lake_monitor
   ```

2. Create and activate a virtual environment (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Linux/Mac
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Run the application:
   ```bash
   python app.py
   ```

2. Open your browser and navigate to:
   ```
   http://localhost:8081
   ```

3. Available pages:
   - `/` - Main dashboard with current status
   - `/chart` - Historical data and trends
   - `/analytics` - Visitor analytics (restricted access)

## Configuration

### Analytics Access Control

Edit the `ALLOWED_ANALYTICS_IPS` list in `app.py` to control who can access the analytics page:

```python
ALLOWED_ANALYTICS_IPS = [
    '69.166.66.114',      # Single IP
    '127.0.0.1',          # Localhost
    '192.168.0.0/24'      # IP range
]
```

## API Endpoints

- `GET /api/status` - Current lake status and elevation
- `GET /api/history` - 30-day historical lake data
- `GET /api/flow-12hr` - River flow data in 12-hour increments
- `GET /api/environment` - Weather, moon phase, and sunrise/sunset data
- `GET /api/stats` - Visitor statistics (used by analytics page)

## Data Sources

### USGS Water Services
- **Canyon Lake**: Station 08167700 (Lake elevation)
- **Guadalupe River**: Station 08167500 (River flow near Spring Branch)
- API: https://waterservices.usgs.gov/nwis/

### Weather Data
- **National Weather Service**: https://api.weather.gov
- No API key required
- Provides temperature and current conditions

### Astronomical Calculations
- **Sunrise/Sunset**: Calculated using astral library for Canyon Lake coordinates
- **Moon Phase**: Calculated based on lunar cycle (29.53 days)

## Technical Details

### Lake Specifications
- **Location**: Canyon Lake, Texas (29.8719°N, 98.2697°W)
- **Conservation Pool Elevation**: 909.0 ft (above NGVD 1929)
- **Flood Pool Elevation**: 943.0 ft
- **Conservation Capacity**: 378,781 acre-feet

### Technology Stack
- **Backend**: Python 3, Flask web framework
- **Frontend**: HTML5, CSS3, JavaScript
- **Charts**: Chart.js
- **Data Storage**: JSON file-based (hits.json)
- **APIs**: USGS Water Services, National Weather Service
- **Libraries**:
  - requests (HTTP requests)
  - astral (sunrise/sunset calculations)
  - ipaddress (IP access control)

### Data Update Intervals
- **USGS lake data**: Real-time (typically 15-60 minute intervals)
- **USGS river flow**: Real-time (15-minute intervals, aggregated to 12-hour periods)
- **Weather data**: On-demand from weather.gov API
- **Page auto-refresh**: Every 5 minutes

## Project Structure

```
canyon_lake_monitor/
├── app.py                    # Flask application and routes
├── canyon_lake_data.py       # Data fetching and processing logic
├── requirements.txt          # Python dependencies
├── hits.json                 # Visitor analytics data (generated)
├── templates/
│   ├── index.html           # Main dashboard
│   ├── chart.html           # Historical data page
│   └── analytics.html       # Analytics dashboard
└── static/
    └── styles.css           # Stylesheet with Caribbean blue theme
```

## Features in Detail

### Day/Night Mode
The application automatically switches between day and night themes based on the calculated sunrise and sunset times for Canyon Lake, Texas. The night mode features:
- Darker background gradient
- Subdued colors for better nighttime viewing
- Maintained readability with adjusted contrast

### Hit Counter and Analytics
All page visits are tracked and stored in `hits.json`:
- Total hit counter
- Unique IP tracking
- Route-specific statistics
- Last 100 visits with timestamps
- Time-based filtering (24h, 7d, all-time)

### IP Address Handling
The application properly handles proxied requests by checking the `X-Forwarded-For` header, ensuring accurate visitor tracking when behind reverse proxies or load balancers.

## Development

To modify the application:

1. Edit `app.py` for routing and Flask configuration
2. Edit `canyon_lake_data.py` for data fetching logic
3. Edit templates in `templates/` for UI changes
4. Edit `static/styles.css` for styling changes

The application runs in debug mode by default when executed directly. For production deployment, consider using a production WSGI server like Gunicorn.

## License

This project is open source and available for personal and educational use.

## Author

Richard Hasting

## Acknowledgments

- USGS for providing free access to water monitoring data
- National Weather Service for weather data
- Chart.js for excellent charting capabilities
