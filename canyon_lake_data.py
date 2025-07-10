import requests
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, List

class CanyonLakeMonitor:
    def __init__(self):
        self.usgs_site_id = "08167700"
        self.base_url = "https://waterservices.usgs.gov/nwis/iv/"
        self.dv_url = "https://waterservices.usgs.gov/nwis/dv/"  # Daily values endpoint
        self.conservation_pool_elevation = 909.0
        self.flood_pool_elevation = 943.0
        self.conservation_capacity = 378781  # acre-feet
    
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
        else:
            status_category = 'low'
        
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

    def fetch_historical_data(self, days: int = 30) -> Optional[List[Dict]]:
        """Fetch historical daily water level data from USGS API"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        params = {
            'sites': self.usgs_site_id,
            'parameterCd': '62614',  # Lake elevation
            'startDT': start_date.strftime('%Y-%m-%d'),
            'endDT': end_date.strftime('%Y-%m-%d'),
            'format': 'json'
        }
        
        try:
            response = requests.get(self.dv_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Parse daily values
            historical_data = []
            time_series = data['value']['timeSeries']
            
            for series in time_series:
                if series['variable']['variableCode'][0]['value'] == '62614':
                    values = series['values'][0]['value']
                    for value in values:
                        date = value['dateTime']
                        elevation = float(value['value'])
                        percentage = self.calculate_percentage_full(elevation)
                        
                        historical_data.append({
                            'date': date,
                            'elevation': elevation,
                            'percentage_full': percentage
                        })
            
            return historical_data
        except (requests.RequestException, KeyError, IndexError, ValueError) as e:
            print(f"Error fetching historical data: {e}")
            return None

if __name__ == "__main__":
    monitor = CanyonLakeMonitor()
    status = monitor.get_lake_status()
    print(json.dumps(status, indent=2))