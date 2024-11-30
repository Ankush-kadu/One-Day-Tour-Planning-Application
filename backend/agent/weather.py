import aiohttp
from typing import Dict, Any,List
from datetime import datetime
from ..config import get_settings

class WeatherAgent:
    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.OPENWEATHERMAP_API_KEY
        self.base_url = "http://api.openweathermap.org/data/2.5"

    async def get_weather_forecast(self, city: str, date: datetime) -> Dict[str, Any]:
        """Get weather forecast for a specific city and date."""
        async with aiohttp.ClientSession() as session:
            # Get coordinates for the city
            coords = await self._get_city_coordinates(session, city)
            if not coords:
                return {"error": "City not found"}

            # Get weather forecast
            forecast = await self._get_forecast(session, coords['lat'], coords['lon'])
            
            # Find the forecast for the specific date
            target_forecast = self._find_date_forecast(forecast, date)
            
            return self._process_forecast(target_forecast)

    async def _get_city_coordinates(self, session: aiohttp.ClientSession, city: str) -> Dict[str, float]:
        """Get latitude and longitude for a city."""
        url = f"{self.base_url}/geo/1.0/direct"
        params = {
            'q': city,
            'limit': 1,
            'appid': self.api_key
        }

        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                if data:
                    return {
                        'lat': data[0]['lat'],
                        'lon': data[0]['lon']
                    }
            return None

    async def _get_forecast(
        self,
        session: aiohttp.ClientSession,
        lat: float,
        lon: float
    ) -> Dict[str, Any]:
        """Get weather forecast for coordinates."""
        url = f"{self.base_url}/forecast"
        params = {
            'lat': lat,
            'lon': lon,
            'appid': self.api_key,
            'units': 'metric'
        }

        async with session.get(url, params=params) as response:
            if response.status == 200:
                return await response.json()
            return None

    def _find_date_forecast(
        self,
        forecast_data: Dict[str, Any],
        target_date: datetime
    ) -> Dict[str, Any]:
        """Find forecast for specific date from forecast data."""
        if not forecast_data or 'list' not in forecast_data:
            return None

        target_date_str = target_date.strftime('%Y-%m-%d')
        
        # Find forecasts for target date
        day_forecasts = [
            f for f in forecast_data['list']
            if datetime.fromtimestamp(f['dt']).strftime('%Y-%m-%d') == target_date_str
        ]

        if not day_forecasts:
            return None

        # Return the forecast for the middle of the day
        return day_forecasts[len(day_forecasts)//2]

    def _process_forecast(self, forecast: Dict[str, Any]) -> Dict[str, Any]:
        """Process and format weather forecast data."""
        if not forecast:
            return {
                'status': 'unavailable',
                'message': 'Weather forecast not available'
            }

        conditions = forecast['weather'][0]
        temp = forecast['main']

        return {
            'status': 'available',
            'temperature': {
                'current': round(temp['temp']),
                'feels_like': round(temp['feels_like']),
                'min': round(temp['temp_min']),
                'max': round(temp['temp_max'])
            },
            'conditions': {
                'main': conditions['main'],
                'description': conditions['description']
            },
            'humidity': temp['humidity'],
            'recommendations': self._generate_recommendations(
                temp['temp'],
                conditions['main'],
                temp['humidity']
            )
        }

    def _generate_recommendations(
        self,
        temperature: float,
        conditions: str,
        humidity: int
    ) -> List[str]:
        """Generate weather-based recommendations."""
        recommendations = []

        # Temperature-based recommendations
        if temperature < 10:
            recommendations.append("Bring warm clothing and layers")
        elif temperature > 30:
            recommendations.append("Bring sun protection and stay hydrated")
        
        # Condition-based recommendations
        if conditions.lower() in ['rain', 'drizzle', 'thunderstorm']:
            recommendations.append("Bring an umbrella and waterproof clothing")
        elif conditions.lower() in ['snow', 'sleet']:
            recommendations.append("Wear winter boots and warm clothing")
        elif conditions.lower() == 'clear':
            recommendations.append("Bring sunglasses and sun protection")
        
        # Humidity-based recommendations
        if humidity > 80:
            recommendations.append("High humidity - dress in light, breathable clothing")

        return recommendations