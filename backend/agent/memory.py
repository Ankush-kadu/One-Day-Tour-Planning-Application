from typing import Dict, Any, List, Optional, Set
import ollama
from datetime import datetime
from ..database.neo4j_client import Neo4jClient

class MemoryAgent:
    def __init__(self):
        self.db = Neo4jClient()

    async def process_interaction(
        self,
        user_id: str,
        message: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process user interaction and extract/store relevant information."""
        
        # Extract entities and relationships from the message
        entities = await self._extract_entities(message)
        relationships = await self._extract_relationships(message, entities)
        
        # Store extracted information in the graph database
        self._store_entities_and_relationships(user_id, entities, relationships)
        
        # Update user preferences based on the interaction
        self._update_user_preferences(user_id, entities, context)
        
        # Return updated context with new information
        return self._build_updated_context(user_id, context, entities, relationships)

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Retrieve comprehensive user profile from memory."""
        with self.db.driver.session() as session:
            # Get user preferences
            preferences = session.run("""
                MATCH (u:User {id: $user_id})-[r:HAS_PREFERENCE]->(p:Preference)
                RETURN p.type as type, p.value as value
                """, user_id=user_id)
            
            # Get past interactions
            interactions = session.run("""
                MATCH (u:User {id: $user_id})-[r:INTERACTED_WITH]->(e:Entity)
                RETURN e.type as type, e.value as value, r.timestamp as timestamp
                ORDER BY r.timestamp DESC LIMIT 10
                """, user_id=user_id)
            
            # Get favorite locations
            locations = session.run("""
                MATCH (u:User {id: $user_id})-[r:VISITED]->(l:Location)
                RETURN l.name as name, l.type as type, r.rating as rating
                ORDER BY r.rating DESC LIMIT 5
                """, user_id=user_id)

            return {
                'preferences': [dict(pref) for pref in preferences],
                'recent_interactions': [dict(inter) for inter in interactions],
                'favorite_locations': [dict(loc) for loc in locations]
            }

    async def update_preferences(
        self,
        user_id: str,
        preferences: Dict[str, Any]
    ) -> None:
        """Update user preferences in the database."""
        with self.db.driver.session() as session:
            for pref_type, value in preferences.items():
                session.run("""
                    MERGE (u:User {id: $user_id})
                    MERGE (p:Preference {type: $type, value: $value})
                    MERGE (u)-[r:HAS_PREFERENCE]->(p)
                    SET r.timestamp = datetime()
                    """, user_id=user_id, type=pref_type, value=value)

    async def get_similar_users(self, user_id: str) -> List[Dict[str, Any]]:
        """Find users with similar preferences and behaviors."""
        with self.db.driver.session() as session:
            similar_users = session.run("""
                MATCH (u1:User {id: $user_id})-[:HAS_PREFERENCE]->(p:Preference)
                MATCH (u2:User)-[:HAS_PREFERENCE]->(p)
                WHERE u1 <> u2
                WITH u2, COUNT(p) as common_preferences
                ORDER BY common_preferences DESC
                LIMIT 5
                RETURN u2.id as user_id, common_preferences
                """, user_id=user_id)
            
            return [dict(user) for user in similar_users]

    async def _extract_entities(self, message: str) -> List[Dict[str, Any]]:
        """Extract entities from user message using Ollama."""
        prompt = f"""
        Extract entities from this message: {message}
        Focus on:
        - Locations (cities, attractions, restaurants)
        - Activities (sightseeing, dining, shopping)
        - Preferences (food types, transportation modes)
        - Time-related information (duration, specific times)
        - Budget-related information
        
        Return a JSON array of entities with:
        - type (location/activity/preference/time/budget)
        - value
        - confidence_score (0-1)
        """
        
        response = ollama.chat(model='llama2', messages=[{
            'role': 'system',
            'content': prompt
        }])
        
        # Process and validate the response
        try:
            return self._parse_entities_response(response['message']['content'])
        except Exception as e:
            print(f"Error extracting entities: {e}")
            return []

    async def _extract_relationships(
        self,
        message: str,
        entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract relationships between entities using Ollama."""
        prompt = f"""
        Extract relationships between these entities: {entities}
        From this message: {message}
        
        Return a JSON array of relationships with:
        - source_entity
        - relationship_type
        - target_entity
        - confidence_score (0-1)
        """
        
        response = ollama.chat(model='llama2', messages=[{
            'role': 'system',
            'content': prompt
        }])
        
        # Process and validate the response
        try:
            return self._parse_relationships_response(response['message']['content'])
        except Exception as e:
            print(f"Error extracting relationships: {e}")
            return []

    def _store_entities_and_relationships(
        self,
        user_id: str,
        entities: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]]
    ) -> None:
        """Store extracted entities and relationships in Neo4j."""
        with self.db.driver.session() as session:
            # Store entities
            for entity in entities:
                session.run("""
                    MERGE (e:Entity {type: $type, value: $value})
                    WITH e
                    MATCH (u:User {id: $user_id})
                    MERGE (u)-[r:INTERACTED_WITH]->(e)
                    SET r.timestamp = datetime(),
                        r.confidence = $confidence
                    """, 
                    type=entity['type'],
                    value=entity['value'],
                    user_id=user_id,
                    confidence=entity.get('confidence_score', 0.5)
                )
            
            # Store relationships
            for rel in relationships:
                session.run("""
                    MATCH (e1:Entity {value: $source})
                    MATCH (e2:Entity {value: $target})
                    MERGE (e1)-[r:RELATES_TO {type: $rel_type}]->(e2)
                    SET r.confidence = $confidence,
                        r.timestamp = datetime()
                    """,
                    source=rel['source_entity'],
                    target=rel['target_entity'],
                    rel_type=rel['relationship_type'],
                    confidence=rel.get('confidence_score', 0.5)
                )

    def _update_user_preferences(
        self,
        user_id: str,
        entities: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> None:
        """Update user preferences based on extracted entities and context."""
        preference_entities = [
            entity for entity in entities
            if entity['type'] == 'preference' and entity.get('confidence_score', 0) > 0.7
        ]
        
        if preference_entities:
            with self.db.driver.session() as session:
                for pref in preference_entities:
                    session.run("""
                        MERGE (u:User {id: $user_id})
                        MERGE (p:Preference {type: $type, value: $value})
                        MERGE (u)-[r:HAS_PREFERENCE]->(p)
                        SET r.timestamp = datetime(),
                            r.confidence = $confidence
                        """,
                        user_id=user_id,
                        type=pref['type'],
                        value=pref['value'],
                        confidence=pref['confidence_score']
                    )

    def _build_updated_context(
        self,
        user_id: str,
        current_context: Dict[str, Any],
        entities: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build updated context based on current context and new information."""
        updated_context = current_context.copy()
        
        # Add new entities to context
        if 'entities' not in updated_context:
            updated_context['entities'] = set()
        updated_context['entities'].update({
            entity['value'] for entity in entities
            if entity.get('confidence_score', 0) > 0.5
        })
        
        # Update preferences
        if 'preferences' not in updated_context:
            updated_context['preferences'] = {}
        for entity in entities:
            if entity['type'] == 'preference' and entity.get('confidence_score', 0) > 0.7:
                updated_context['preferences'][entity['value']] = entity['confidence_score']
        
        # Add timestamp
        updated_context['last_updated'] = datetime.now().isoformat()
        
        return updated_context

    def _parse_entities_response(self, response_content: str) -> List[Dict[str, Any]]:
        """Parse and validate entities from Ollama response."""
        # In a real application, you'd implement proper JSON parsing and validation
        # This is a simplified version
        try:
            # Implement proper parsing logic here
            return []
        except Exception as e:
            print(f"Error parsing entities response: {e}")
            return []

    def _parse_relationships_response(self, response_content: str) -> List[Dict[str, Any]]:
        """Parse and validate relationships from Ollama response."""
        # In a real application, you'd implement proper JSON parsing and validation
        # This is a simplified version
        try:
            # Implement proper parsing logic here
            return []
        except Exception as e:
            print(f"Error parsing relationships response: {e}")
            return []