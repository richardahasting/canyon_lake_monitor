# Canyon Lake Water Level Monitor

A Python and HTML application that displays the current water level of Canyon Lake in Texas.

## Features

- Real-time water level data from USGS
- Visual representation of lake fullness
- Color-coded status indicators:
  - **Flood** (red): Above flood stage
  - **Full** (blue): At conservation capacity
  - **Excellent** (blue): 90-100% full
  - **Good** (green): 75-90% full
  - **Low** (orange): Below 75% full
- Current elevation and feet below conservation pool
- Auto-refresh every 5 minutes

## Installation

1. Install Python 3.7 or higher

2. Install dependencies:
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
   http://localhost:5000
   ```

## How it Works

- **Data Source**: USGS monitoring station 08167700 (Canyon Lake near New Braunfels, TX)
- **API**: USGS Water Services REST API
- **Backend**: Python Flask server that fetches and processes USGS data
- **Frontend**: HTML/CSS/JavaScript with animated water level visualization

## Technical Details

- Conservation Pool Elevation: 909.0 ft
- Flood Pool Elevation: 943.0 ft
- Conservation Capacity: 378,781 acre-feet
- Data updates: Real-time from USGS (typically 15-60 minute intervals)