from typing import List, Dict, Any
from datetime import datetime, timedelta
import aiohttp
import json
from ..database.neo4j_client import Neo4jClient

class NewsAgent:
    def __init__(self):
        self.db = Neo4jClient()
        self.cache_duration = timedelta(hours=1)
        self.cache = {}

    async def get_relevant_news(self, city: str, date: datetime) -> List[Dict[str, Any]]:
        """Get relevant news that might affect tourism in the city."""
        try:
            # Check cache first
            cache_key = f"{city}_{date.date()}"
            if cache_key in self.cache:
                cached_data = self.cache[cache_key]
                if datetime.now() - cached_data['timestamp'] < self.cache_duration:
                    return cached_data['data']

            # Get news from multiple sources
            news_items = await self._gather_news(city)
            
            # Get events from database
            events = self._get_city_events(city, date)
            
            # Combine and process all information
            relevant_info = self._process_information(news_items, events, date)
            
            # Cache the results
            self.cache[cache_key] = {
                'timestamp': datetime.now(),
                'data': relevant_info
            }
            
            return relevant_info

        except Exception as e:
            print(f"Error getting news: {e}")
            return []

    async def _gather_news(self, city: str) -> List[Dict[str, Any]]:
        """Gather news from various sources."""
        news_items = []
        
        # Simulated news data - in production, you'd integrate with real news APIs
        simulated_news = [
            {
                'title': f'Major Festival in {city}',
                'description': f'Annual cultural festival in {city} starting next week',
                'impact_level': 'medium',
                'category': 'event',
                'affected_areas': ['city center'],
                'recommendations': ['Book accommodations early', 'Expect crowds']
            },
            {
                'title': f'Transportation Update in {city}',
                'description': 'Public transportation improvements ongoing',
                'impact_level': 'low',
                'category': 'transport',
                'affected_areas': ['metro lines'],
                'recommendations': ['Check route updates', 'Allow extra travel time']
            }
        ]
        
        news_items.extend(simulated_news)
        return news_items

    def _get_city_events(self, city: str, date: datetime) -> List[Dict[str, Any]]:
        """Get events from the database."""
        try:
            with self.db.driver.session() as session:
                query = """
                MATCH (e:Event)
                WHERE e.city = $city 
                AND date(e.start_date) <= date($date)
                AND date(e.end_date) >= date($date)
                RETURN e
                """
                result = session.run(query, 
                    city=city,
                    date=date.strftime("%Y-%m-%d")
                )
                return [dict(record['e']) for record in result]
        except Exception as e:
            print(f"Error getting events from database: {e}")
            return []

    def _process_information(
        self,
        news_items: List[Dict[str, Any]],
        events: List[Dict[str, Any]],
        target_date: datetime
    ) -> List[Dict[str, Any]]:
        """Process and filter relevant information."""
        processed_items = []
        
        # Process news items
        for item in news_items:
            if self._is_relevant(item, target_date):
                processed_items.append({
                    'type': 'news',
                    'title': item['title'],
                    'description': item['description'],
                    'impact_level': item['impact_level'],
                    'recommendations': item.get('recommendations', []),
                    'affected_areas': item.get('affected_areas', [])
                })
        
        # Process events
        for event in events:
            processed_items.append({
                'type': 'event',
                'title': event['title'],
                'description': event.get('description', ''),
                'impact_level': event.get('impact_level', 'low'),
                'location': event.get('location', ''),
                'start_time': event.get('start_time', ''),
                'end_time': event.get('end_time', '')
            })
        
        # Sort by impact level
        impact_levels = {'high': 3, 'medium': 2, 'low': 1}
        processed_items.sort(
            key=lambda x: impact_levels.get(x['impact_level'], 0),
            reverse=True
        )
        
        return processed_items

    def _is_relevant(self, item: Dict[str, Any], target_date: datetime) -> bool:
        """Determine if a news item is relevant for the target date."""
        # Add relevance criteria here
        return True

    async def check_location_status(self, location_name: str) -> Dict[str, Any]:
        """Check if a specific location has any alerts or special notices."""
        try:
            with self.db.driver.session() as session:
                query = """
                MATCH (l:Location {name: $location_name})
                RETURN l.status as status, 
                       l.last_updated as last_updated,
                       l.alerts as alerts
                """
                result = session.run(query, location_name=location_name).single()
                
                if result:
                    return {
                        'status': result['status'],
                        'last_updated': result['last_updated'],
                        'alerts': result['alerts']
                    }
                return {
                    'status': 'unknown',
                    'alerts': []
                }
        except Exception as e:
            print(f"Error checking location status: {e}")
            return {
                'status': 'error',
                'alerts': [f"Error checking status: {str(e)}"]
            }

    def store_alert(self, alert_data: Dict[str, Any]) -> bool:
        """Store a new alert in the database."""
        try:
            with self.db.driver.session() as session:
                query = """
                CREATE (a:Alert {
                    id: randomUUID(),
                    title: $title,
                    description: $description,
                    impact_level: $impact_level,
                    created_at: datetime(),
                    expires_at: datetime($expires_at)
                })
                WITH a
                MATCH (l:Location {name: $location})
                CREATE (a)-[:AFFECTS]->(l)
                RETURN a.id
                """
                result = session.run(query, 
                    title=alert_data['title'],
                    description=alert_data['description'],
                    impact_level=alert_data['impact_level'],
                    expires_at=alert_data['expires_at'],
                    location=alert_data['location']
                )
                return bool(result.single())
        except Exception as e:
            print(f"Error storing alert: {e}")
            return False