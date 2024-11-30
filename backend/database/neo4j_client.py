from neo4j import GraphDatabase
from typing import List, Dict, Any, Optional
from datetime import datetime

class Neo4jClient:
    def __init__(self):
        self.uri = "bolt://localhost:7687"  # Default Neo4j URI
        self.user = "neo4j"                 # Default username
        self.password = "11111111"      # Replace with your password
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def test_connection(self) -> bool:
        """Test if database connection is working"""
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1")
                return bool(result.single()[0] == 1)
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False

    def store_user_preference(self, user_id: str, preference_type: str, value: str) -> None:
        """Store user preference in database"""
        with self.driver.session() as session:
            query = """
            MERGE (u:User {id: $user_id})
            MERGE (p:Preference {type: $pref_type, value: $value})
            MERGE (u)-[r:HAS_PREFERENCE]->(p)
            SET r.updated_at = datetime()
            """
            session.run(query, user_id=user_id, pref_type=preference_type, value=value)

    def get_user_preferences(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user preferences from database"""
        with self.driver.session() as session:
            query = """
            MATCH (u:User {id: $user_id})-[r:HAS_PREFERENCE]->(p:Preference)
            RETURN p.type as type, p.value as value, r.updated_at as updated_at
            ORDER BY r.updated_at DESC
            """
            result = session.run(query, user_id=user_id)
            return [dict(record) for record in result]

    def store_itinerary(self, user_id: str, itinerary_data: Dict[str, Any]) -> str:
        """Store itinerary in database"""
        with self.driver.session() as session:
            query = """
            MATCH (u:User {id: $user_id})
            CREATE (i:Itinerary {
                id: randomUUID(),
                date: datetime($date),
                city: $city,
                budget: $budget,
                created_at: datetime()
            })
            CREATE (u)-[:HAS_ITINERARY]->(i)
            RETURN i.id as itinerary_id
            """
            result = session.run(
                query,
                user_id=user_id,
                date=itinerary_data['date'],
                city=itinerary_data['city'],
                budget=itinerary_data['budget']
            )
            return result.single()['itinerary_id']

    def close(self):
        """Close the database connection"""
        self.driver.close()