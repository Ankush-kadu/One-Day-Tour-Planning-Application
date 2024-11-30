from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any

# Updated relative imports
from .agents.user_interaction import UserInteractionAgent
from .agents.itinerary_generation import ItineraryGenerationAgent
from .models.schemas import Itinerary
from .config import get_settings

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize settings and agents
settings = get_settings()
user_agent = UserInteractionAgent()
itinerary_agent = ItineraryGenerationAgent()

@app.post("/chat")
async def chat_endpoint(request: Dict[str, Any]):
    try:
        response = await user_agent.process_user_input(
            user_id=request["user_id"],
            message=request["message"],
            context=request.get("current_itinerary")
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user/{user_id}/itineraries")
async def get_user_itineraries(user_id: str):
    try:
        return []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))