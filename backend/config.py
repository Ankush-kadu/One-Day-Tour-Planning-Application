from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "11111111"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OPENWEATHERMAP_API_KEY: str = "c3c056dcc30b6a75079d6e5526f34006"
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()