from .neo4j_client import Neo4jClient

__all__ = ['Neo4jClient']

# Optional: You can add configuration or initialization code here
def init_database():
    """Initialize database connections."""
    try:
        client = Neo4jClient()
        # Test connection
        client.test_connection()
        return client
    except Exception as e:
        raise Exception(f"Failed to initialize database: {str(e)}")

# Optional: Create a default client instance
default_client = None
try:
    default_client = init_database()
except Exception as e:
    print(f"Warning: Could not initialize default database client: {str(e)}")