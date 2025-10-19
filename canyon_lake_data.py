import requests
import json
import os
import math
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from astral import LocationInfo
from astral.sun import sun

class CanyonLakeMonitor:
    def __init__(self):
        self.usgs_site_id = "08167700"
        self.guadalupe_site_id = "08167500"  # Guadalupe River near Spring Branch
        self.base_url = "https://waterservices.usgs.gov/nwis/iv/"
        self.dv_url = "https://waterservices.usgs.gov/nwis/dv/"  # Daily values endpoint
        self.conservation_pool_elevation = 909.0
        self.flood_pool_elevation = 943.0
        self.conservation_capacity = 378781  # acre-feet

        # Location information for Canyon Lake, TX
        self.latitude = 29.8719
        self.longitude = -98.2697
        self.location = LocationInfo("Canyon Lake", "Texas", "America/Chicago",
                                     self.latitude, self.longitude)

        # Weather.gov API (National Weather Service - no API key needed)
        self.weather_base_url = "https://api.weather.gov"
    
    def fetch_current_data(self) -> Optional[Dict]:
        """Fetch current water level data from USGS API"""
        params = {
            'sites': self.usgs_site_id,
            'parameterCd': '62614',  # Lake or reservoir water surface elevation above NGVD 1929
            'format': 'json'
        }
        
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching data: {e}")
            return None
    
    def parse_water_level(self, data: Dict) -> Optional[float]:
        """Extract water level from USGS API response"""
        try:
            time_series = data['value']['timeSeries']
            for series in time_series:
                if series['variable']['variableCode'][0]['value'] == '62614':
                    values = series['values'][0]['value']
                    if values:
                        return float(values[0]['value'])
        except (KeyError, IndexError, ValueError):
            pass
        return None
    
    def calculate_percentage_full(self, current_elevation: float) -> float:
        """Calculate percentage full based on elevation"""
        # Linear approximation between empty and conservation pool
        # Assuming empty at elevation 860 ft (approximation)
        empty_elevation = 860.0
        
        if current_elevation >= self.conservation_pool_elevation:
            return 100.0
        elif current_elevation <= empty_elevation:
            return 0.0
        else:
            percentage = ((current_elevation - empty_elevation) / 
                         (self.conservation_pool_elevation - empty_elevation)) * 100
            return round(percentage, 1)
    
    def get_lake_status(self) -> Dict:
        """Get comprehensive lake status"""
        data = self.fetch_current_data()
        
        if not data:
            return {
                'status': 'error',
                'message': 'Unable to fetch data from USGS'
            }
        
        current_elevation = self.parse_water_level(data)
        
        if current_elevation is None:
            return {
                'status': 'error',
                'message': 'Unable to parse water level data'
            }
        
        percentage_full = self.calculate_percentage_full(current_elevation)
        
        # Determine status category - adjusted thresholds
        if current_elevation >= self.flood_pool_elevation:
            status_category = 'flood'
        elif current_elevation >= self.conservation_pool_elevation:
            status_category = 'full'
        elif percentage_full >= 90:
            status_category = 'excellent'
        elif percentage_full >= 75:
            status_category = 'good'
        elif percentage_full >= 40:
            status_category = 'low'
        else:
            status_category = 'critical'
        
        return {
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'elevation': current_elevation,
            'percentage_full': percentage_full,
            'status_category': status_category,
            'conservation_pool': self.conservation_pool_elevation,
            'flood_pool': self.flood_pool_elevation,
            'feet_below_conservation': round(self.conservation_pool_elevation - current_elevation, 2)
        }

    def fetch_historical_data(self, days: int = 30) -> Optional[Dict]:
        """Fetch historical daily water level and river flow data from USGS API"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Fetch lake elevation data (daily values)
        lake_params = {
            'sites': self.usgs_site_id,
            'parameterCd': '62614',  # Lake elevation
            'startDT': start_date.strftime('%Y-%m-%d'),
            'endDT': end_date.strftime('%Y-%m-%d'),
            'format': 'json'
        }
        
        # Fetch river flow data (instantaneous values for 12-hour increments)
        river_params = {
            'sites': self.guadalupe_site_id,
            'parameterCd': '00060',  # Streamflow in cfs
            'startDT': start_date.strftime('%Y-%m-%d'),
            'endDT': end_date.strftime('%Y-%m-%d'),
            'format': 'json'
        }
        
        try:
            # Get lake data
            lake_response = requests.get(self.dv_url, params=lake_params)
            lake_response.raise_for_status()
            lake_data = lake_response.json()
            
            # Get river flow data
            river_response = requests.get(self.dv_url, params=river_params)
            river_response.raise_for_status()
            river_data = river_response.json()
            
            # Parse lake elevation data
            elevation_by_date = {}
            lake_time_series = lake_data['value']['timeSeries']
            
            for series in lake_time_series:
                if series['variable']['variableCode'][0]['value'] == '62614':
                    values = series['values'][0]['value']
                    for value in values:
                        date = value['dateTime']
                        elevation = float(value['value'])
                        percentage = self.calculate_percentage_full(elevation)
                        
                        elevation_by_date[date] = {
                            'date': date,
                            'elevation': elevation,
                            'percentage_full': percentage
                        }
            
            # Parse river flow data
            flow_by_date = {}
            river_time_series = river_data['value']['timeSeries']
            
            for series in river_time_series:
                if series['variable']['variableCode'][0]['value'] == '00060':
                    values = series['values'][0]['value']
                    for value in values:
                        date = value['dateTime']
                        flow = float(value['value'])
                        flow_by_date[date] = flow
            
            # Combine data
            combined_data = []
            for date, lake_info in elevation_by_date.items():
                lake_info['river_flow'] = flow_by_date.get(date, None)
                combined_data.append(lake_info)
            
            # Sort by date
            combined_data.sort(key=lambda x: x['date'])
            
            return {
                'lake_data': combined_data,
                'river_flow_data': flow_by_date
            }
            
        except (requests.RequestException, KeyError, IndexError, ValueError) as e:
            print(f"Error fetching historical data: {e}")
            return None
    
    def fetch_river_flow_12hr(self, days: int = 30) -> Optional[List[Dict]]:
        """Fetch river flow data in 12-hour increments"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        params = {
            'sites': self.guadalupe_site_id,
            'parameterCd': '00060',  # Streamflow in cfs
            'startDT': start_date.strftime('%Y-%m-%d'),
            'endDT': end_date.strftime('%Y-%m-%d'),
            'format': 'json'
        }
        
        try:
            # Get instantaneous values
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Parse flow data
            flow_data = []
            time_series = data['value']['timeSeries']
            
            for series in time_series:
                if series['variable']['variableCode'][0]['value'] == '00060':
                    values = series['values'][0]['value']
                    for value in values:
                        timestamp = datetime.fromisoformat(value['dateTime'].replace('Z', '+00:00'))
                        flow = float(value['value'])
                        flow_data.append({
                            'timestamp': timestamp,
                            'flow': flow
                        })
            
            # Sort by timestamp
            flow_data.sort(key=lambda x: x['timestamp'])
            
            # Aggregate into 12-hour periods
            aggregated_data = []
            if flow_data:
                current_period_start = flow_data[0]['timestamp'].replace(
                    hour=0 if flow_data[0]['timestamp'].hour < 12 else 12,
                    minute=0, second=0, microsecond=0
                )
                current_values = []
                
                for item in flow_data:
                    period_start = item['timestamp'].replace(
                        hour=0 if item['timestamp'].hour < 12 else 12,
                        minute=0, second=0, microsecond=0
                    )
                    
                    if period_start != current_period_start:
                        # Calculate average for the period
                        if current_values:
                            avg_flow = sum(current_values) / len(current_values)
                            aggregated_data.append({
                                'timestamp': current_period_start.isoformat(),
                                'flow': round(avg_flow, 2),
                                'period': '00:00-12:00' if current_period_start.hour == 0 else '12:00-24:00'
                            })
                        
                        current_period_start = period_start
                        current_values = [item['flow']]
                    else:
                        current_values.append(item['flow'])
                
                # Don't forget the last period
                if current_values:
                    avg_flow = sum(current_values) / len(current_values)
                    aggregated_data.append({
                        'timestamp': current_period_start.isoformat(),
                        'flow': round(avg_flow, 2),
                        'period': '00:00-12:00' if current_period_start.hour == 0 else '12:00-24:00'
                    })
            
            return aggregated_data
            
        except (requests.RequestException, KeyError, IndexError, ValueError) as e:
            print(f"Error fetching 12-hour flow data: {e}")
            return None

    def fetch_weather(self) -> Optional[Dict]:
        """Fetch current weather data from Weather.gov API (National Weather Service)"""
        try:
            # First, get the grid point data for our location
            points_url = f"{self.weather_base_url}/points/{self.latitude},{self.longitude}"
            headers = {
                'User-Agent': '(Canyon Lake Monitor, contact@example.com)',
                'Accept': 'application/json'
            }

            points_response = requests.get(points_url, headers=headers, timeout=10)
            points_response.raise_for_status()
            points_data = points_response.json()

            # Get the observation stations URL
            observation_stations_url = points_data['properties']['observationStations']

            # Fetch the nearest observation station
            stations_response = requests.get(observation_stations_url, headers=headers, timeout=10)
            stations_response.raise_for_status()
            stations_data = stations_response.json()

            if not stations_data['features']:
                raise ValueError("No observation stations found")

            # Get the latest observation from the nearest station
            station_id = stations_data['features'][0]['properties']['stationIdentifier']
            observation_url = f"{self.weather_base_url}/stations/{station_id}/observations/latest"

            obs_response = requests.get(observation_url, headers=headers, timeout=10)
            obs_response.raise_for_status()
            obs_data = obs_response.json()

            # Extract temperature (convert from Celsius to Fahrenheit)
            temp_c = obs_data['properties']['temperature']['value']
            if temp_c is not None:
                temp_f = (temp_c * 9/5) + 32
                temperature = round(temp_f, 1)
            else:
                temperature = None

            # Get weather description
            description = obs_data['properties']['textDescription']
            if not description:
                description = 'Clear'

            return {
                'temperature': temperature,
                'feels_like': None,  # Weather.gov doesn't provide "feels like"
                'description': description,
                'station': station_id
            }

        except (requests.RequestException, KeyError, ValueError, TypeError) as e:
            print(f"Error fetching weather data from weather.gov: {e}")
            return {
                'temperature': None,
                'description': 'Unable to fetch weather',
                'feels_like': None
            }

    def calculate_moon_phase(self, date: Optional[datetime] = None) -> Dict:
        """Calculate moon phase for given date (or today)"""
        if date is None:
            date = datetime.now()

        # Known new moon reference point
        known_new_moon = datetime(2000, 1, 6, 18, 14)
        lunar_cycle = 29.53058867  # days

        # Calculate days since known new moon
        days_since = (date - known_new_moon).total_seconds() / 86400
        phase_position = (days_since % lunar_cycle) / lunar_cycle

        # Determine phase name and emoji
        if phase_position < 0.0625:
            phase_name = "New Moon"
            emoji = "🌑"
        elif phase_position < 0.1875:
            phase_name = "Waxing Crescent"
            emoji = "🌒"
        elif phase_position < 0.3125:
            phase_name = "First Quarter"
            emoji = "🌓"
        elif phase_position < 0.4375:
            phase_name = "Waxing Gibbous"
            emoji = "🌔"
        elif phase_position < 0.5625:
            phase_name = "Full Moon"
            emoji = "🌕"
        elif phase_position < 0.6875:
            phase_name = "Waning Gibbous"
            emoji = "🌖"
        elif phase_position < 0.8125:
            phase_name = "Last Quarter"
            emoji = "🌗"
        elif phase_position < 0.9375:
            phase_name = "Waning Crescent"
            emoji = "🌘"
        else:
            phase_name = "New Moon"
            emoji = "🌑"

        return {
            'phase_name': phase_name,
            'emoji': emoji,
            'illumination': round(abs(0.5 - phase_position) * 200, 1)
        }

    def is_daytime(self) -> Dict:
        """Determine if it's currently daytime based on sun position"""
        try:
            now = datetime.now(self.location.tzinfo)
            sun_times = sun(self.location.observer, date=now.date(), tzinfo=self.location.tzinfo)

            is_day = sun_times['sunrise'] <= now <= sun_times['sunset']

            return {
                'is_daytime': is_day,
                'sunrise': sun_times['sunrise'].strftime('%H:%M'),
                'sunset': sun_times['sunset'].strftime('%H:%M')
            }
        except Exception as e:
            print(f"Error calculating day/night: {e}")
            # Fallback to simple time check (6 AM - 8 PM)
            hour = datetime.now().hour
            return {
                'is_daytime': 6 <= hour <= 20,
                'sunrise': '06:00',
                'sunset': '20:00'
            }

    def get_environment_data(self) -> Dict:
        """Get all environmental data: weather, moon phase, and day/night status"""
        weather = self.fetch_weather()
        moon = self.calculate_moon_phase()
        daylight = self.is_daytime()

        return {
            'status': 'success',
            'temperature': weather.get('temperature'),
            'weather_description': weather.get('description'),
            'feels_like': weather.get('feels_like'),
            'moon_phase': moon['phase_name'],
            'moon_emoji': moon['emoji'],
            'moon_illumination': moon['illumination'],
            'is_daytime': daylight['is_daytime'],
            'sunrise': daylight['sunrise'],
            'sunset': daylight['sunset']
        }

if __name__ == "__main__":
    monitor = CanyonLakeMonitor()
    status = monitor.get_lake_status()
    print(json.dumps(status, indent=2))