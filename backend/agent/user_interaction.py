from typing import Dict, Any, Optional, List
from datetime import datetime
# Updated relative imports
from ..database.neo4j_client import Neo4jClient
from ..models.schemas import UserPreference, Location, Itinerary
import json

class UserInteractionAgent:
    def __init__(self):
        self.db = Neo4jClient()
        self.preference_types = {
            'historical': ['museum', 'monument', 'ruins', 'castle', 'palace'],
            'food': ['restaurant', 'cafe', 'food tour', 'market'],
            'shopping': ['mall', 'market', 'shopping street', 'boutique'],
            'nature': ['park', 'garden', 'mountain', 'beach'],
            'entertainment': ['theater', 'concert', 'show', 'nightlife']
        }
    
    # Rest of your UserInteractionAgent implementation
    async def process_user_input(
        self, 
        user_id: str, 
        message: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process user input and manage conversation flow"""
        try:
            # Get user's existing preferences and history
            user_preferences = self.db.get_user_preferences(user_id)
            
            # Extract information from current message
            extracted_info = self._extract_travel_info(message)
            
            # Update user preferences if new ones are found
            if extracted_info.get('preferences'):
                for pref_type, value in extracted_info['preferences'].items():
                    self.db.store_user_preference(user_id, pref_type, str(value))
            
            # Generate appropriate response
            response_data = self._generate_response(
                user_id=user_id,
                extracted_info=extracted_info,
                existing_preferences=user_preferences,
                context=context
            )
            
            # Store interaction in database
            self._store_interaction(user_id, message, extracted_info, response_data)
            
            return response_data
            
        except Exception as e:
            print(f"Error processing user input: {e}")
            return {
                'response_message': "I apologize, but I encountered an error processing your request. Could you try rephrasing that?",
                'extracted_info': {},
                'next_required_info': []
            }

    def _extract_travel_info(self, message: str) -> Dict[str, Any]:
        """Extract travel-related information from user message"""
        info = {}
        message = message.lower()
        
        # Extract city
        cities = self._extract_cities(message)
        if cities:
            info['city'] = cities[0]
        
        # Extract dates
        dates = self._extract_dates(message)
        if dates:
            info['date'] = dates[0]
        
        # Extract time preferences
        times = self._extract_times(message)
        if times:
            info['start_time'] = times.get('start')
            info['end_time'] = times.get('end')
        
        # Extract budget
        budget = self._extract_budget(message)
        if budget:
            info['budget'] = budget
        
        # Extract preferences and interests
        preferences = self._extract_preferences(message)
        if preferences:
            info['preferences'] = preferences
        
        # Extract starting point
        starting_point = self._extract_starting_point(message)
        if starting_point:
            info['starting_point'] = starting_point
        
        return info

    def _store_interaction(
        self,
        user_id: str,
        message: str,
        extracted_info: Dict[str, Any],
        response_data: Dict[str, Any]
    ):
        """Store user interaction in the database"""
        try:
            interaction_data = {
                'timestamp': datetime.now().isoformat(),
                'message': message,
                'extracted_info': json.dumps(extracted_info),
                'response': json.dumps(response_data)
            }
            self.db.store_user_interaction(user_id, interaction_data)
        except Exception as e:
            print(f"Error storing interaction: {e}")

    def _generate_response(
        self,
        user_id: str,
        extracted_info: Dict[str, Any],
        existing_preferences: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate appropriate response based on available information"""
        next_required = self._determine_next_required_info(extracted_info)
        
        # If we have an existing context, merge it with new information
        if context:
            merged_info = {**context, **extracted_info}
        else:
            merged_info = extracted_info
        
        response_message = self._generate_response_message(
            merged_info,
            next_required,
            existing_preferences
        )
        
        return {
            'extracted_info': extracted_info,
            'next_required_info': next_required,
            'response_message': response_message,
            'context': merged_info
        }

    def _extract_cities(self, message: str) -> List[str]:
        """Extract city names from message"""
        # This would be more sophisticated in production
        common_cities = {
            'rome': 'Rome',
            'paris': 'Paris',
            'london': 'London',
            'tokyo': 'Tokyo',
            'new york': 'New York',
            'bangkok': 'Bangkok'
        }
        
        found_cities = []
        for city_key, city_name in common_cities.items():
            if city_key in message.lower():
                found_cities.append(city_name)
        
        return found_cities

    def _extract_dates(self, message: str) -> List[str]:
        """Extract dates from message"""
        # Simple date extraction - would be more sophisticated in production
        from datetime import datetime, timedelta
        
        dates = []
        if 'tomorrow' in message:
            dates.append((datetime.now() + timedelta(days=1)).date().isoformat())
        if 'next week' in message:
            dates.append((datetime.now() + timedelta(days=7)).date().isoformat())
            
        return dates

    def _extract_times(self, message: str) -> Dict[str, str]:
        """Extract time preferences from message"""
        times = {}
        
        # Simple time extraction - would be more sophisticated in production
        if '9am' in message or '9 am' in message:
            times['start'] = '09:00'
        if '5pm' in message or '5 pm' in message:
            times['end'] = '17:00'
            
        return times

    def _extract_budget(self, message: str) -> Optional[float]:
        """Extract budget information from message"""
        import re
        
        # Look for currency amounts
        matches = re.findall(r'\$(\d+(?:\.\d{2})?)', message)
        if matches:
            return float(matches[0])
        
        return None

    def _extract_preferences(self, message: str) -> Dict[str, List[str]]:
        """Extract user preferences and interests"""
        preferences = {}
        
        for pref_type, keywords in self.preference_types.items():
            for keyword in keywords:
                if keyword in message.lower():
                    if pref_type not in preferences:
                        preferences[pref_type] = []
                    preferences[pref_type].append(keyword)
        
        return preferences

    def _extract_starting_point(self, message: str) -> Optional[Dict[str, Any]]:
        """Extract starting point information"""
        if 'hotel' in message.lower():
            # Simple hotel extraction - would be more sophisticated in production
            return {
                'type': 'hotel',
                'name': 'Unknown Hotel',
                'needs_clarification': True
            }
        return None

    def _determine_next_required_info(self, current_info: Dict[str, Any]) -> List[str]:
        """Determine what information is still needed"""
        needed = []
        
        # Essential information
        if 'city' not in current_info:
            needed.append('city')
        if 'date' not in current_info:
            needed.append('date')
        if 'budget' not in current_info:
            needed.append('budget')
        if 'preferences' not in current_info:
            needed.append('interests')
        
        # Optional but useful information
        if 'start_time' not in current_info:
            needed.append('start_time')
        if 'end_time' not in current_info:
            needed.append('end_time')
            
        return needed

    def _generate_response_message(
        self,
        info: Dict[str, Any],
        needed_info: List[str],
        existing_preferences: List[Dict[str, Any]]
    ) -> str:
        """Generate appropriate response message"""
        if not info:
            return "Hi! I'd be happy to help you plan your trip. Which city would you like to visit?"
        
        if 'city' not in info:
            return "Could you tell me which city you'd like to visit?"
            
        if 'date' not in info:
            return f"Great choice! When would you like to visit {info['city']}?"
            
        if 'budget' not in info:
            return "What's your budget for this trip?"
            
        if 'preferences' not in info and not existing_preferences:
            return """What are your interests? For example:
- Historical sites (museums, monuments)
- Food experiences (restaurants, food tours)
- Shopping
- Nature and parks
- Entertainment"""
            
        if len(needed_info) == 0:
            return f"Perfect! I'll create an itinerary for your trip to {info['city']}."
            
        return f"I need a few more details for your {info['city']} trip: {', '.join(needed_info)}"

    def get_user_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Retrieve user's interaction history"""
        try:
            return self.db.get_user_interactions(user_id)
        except Exception as e:
            print(f"Error retrieving user history: {e}")
            return []
# from typing import Dict, Any, Optional
# import ollama
# from ..config import get_settings
# from ..database.neo4j_client import Neo4jClient

# class UserInteractionAgent:
#     def __init__(self):
#         self.db = Neo4jClient()
#         self.settings = get_settings()

#     async def process_user_input(self, user_id: str, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
#         # Process user input using Ollama
#         response = ollama.chat(model='llama2', messages=[{
#             'role': 'system',
#             'content': 'You are a travel planning assistant. Extract relevant information from user messages.'
#         }, {
#             'role': 'user',
#             'content': message
#         }])

#         # Extract information using function calling
#         extracted_info = self._extract_travel_info(response['message']['content'])
        
#         # Store preferences
#         if extracted_info.get('preferences'):
#             for pref_type, value in extracted_info['preferences'].items():
#                 self.db.store_user_preference(user_id, pref_type, value)

#         return {
#             'extracted_info': extracted_info,
#             'next_required_info': self._determine_next_required_info(extracted_info),
#             'response_message': self._generate_response_message(extracted_info)
#         }

#     def _extract_travel_info(self, message: str) -> Dict[str, Any]:
#         # Implement extraction logic using Ollama function calling
#         prompt = f"""
#         Extract travel information from this message: {message}
#         Return a JSON object with the following fields if present:
#         - city
#         - date
#         - start_time
#         - end_time
#         - budget
#         - interests
#         - starting_point
#         """
        
#         response = ollama.chat(model='llama2', messages=[{
#             'role': 'system',
#             'content': prompt
#         }])

#         # Parse the response and return structured data
#         # This is a simplified version - you'd need to add proper JSON parsing
#         return {}

#     def _determine_next_required_info(self, current_info: Dict[str, Any]) -> List[str]:
#         required_fields = ['city', 'date', 'start_time', 'end_time', 'budget', 'interests']
#         missing_fields = [field for field in required_fields if field not in current_info]
#         return missing_fields

#     def _generate_response_message(self, extracted_info: Dict[str, Any]) -> str:
#         # Generate appropriate response based on extracted information
#         if not extracted_info:
#             return "Could you tell me which city you'd like to visit and when?"
        
#         missing_fields = self._determine_next_required_info(extracted_info)
#         if missing_fields:
#             if 'budget' in missing_fields:
#                 return "What's your budget for the day?"
#             if 'interests' in missing_fields:
#                 return "What are your interests? For example: historical sites, food, shopping, or nature?"
            
#         return "Great! Let me create an itinerary based on your preferences."