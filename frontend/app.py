import streamlit as st
import requests
from datetime import datetime, time
import json
import folium
from streamlit_folium import st_folium
from typing import Dict, Any, List

def init_session_state():
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'current_itinerary' not in st.session_state:
        st.session_state.current_itinerary = None
    if 'previous_itineraries' not in st.session_state:
        st.session_state.previous_itineraries = []

def login_page():
    st.title("Tour Planner - Login")
    st.write("Welcome to your personalized tour planning assistant!")
    
    with st.container():
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            if st.button("Login"):
                # In a real application, you'd validate credentials against a database
                st.session_state.user_id = username
                st.success("Logged in successfully!")
                # Fetch user's previous itineraries
                try:
                    response = requests.get(
                        f"http://localhost:8000/user/{username}/itineraries"
                    )
                    if response.ok:
                        st.session_state.previous_itineraries = response.json()
                except Exception as e:
                    st.error(f"Failed to fetch previous itineraries: {str(e)}")
                st.rerun()
        
        with col2:
            if st.button("Create New Account"):
                st.info("Account creation functionality would be implemented here")

def chat_interface():
    st.title("Tour Planner Chat")
    
    # Sidebar with user information and preferences
    with st.sidebar:
        st.subheader(f"Welcome, {st.session_state.user_id}!")
        st.divider()
        
        if st.button("Start New Trip"):
            st.session_state.current_itinerary = None
            st.session_state.chat_history = []
            st.rerun()
        
        if st.session_state.previous_itineraries:
            st.subheader("Previous Trips")
            for prev_itinerary in st.session_state.previous_itineraries:
                if st.button(f"{prev_itinerary['city']} - {prev_itinerary['date']}"):
                    st.session_state.current_itinerary = prev_itinerary
                    st.rerun()
    
    # Main chat area
    chat_container = st.container()
    with chat_container:
        # Display chat history
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.write(message["content"])
                
                # If the message contains weather info, display it in a special way
                if "weather" in message.get("metadata", {}):
                    weather = message["metadata"]["weather"]
                    with st.expander("Weather Information"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Temperature", f"{weather['temperature']['current']}°C")
                            st.write(f"Conditions: {weather['conditions']['description']}")
                        with col2:
                            for rec in weather['recommendations']:
                                st.info(rec)
    
    # Current itinerary display
    if st.session_state.current_itinerary:
        display_itinerary()
    
    # Chat input
    if prompt := st.chat_input("What's your message?"):
        # Add user message to chat history
        st.session_state.chat_history.append({
            "role": "user",
            "content": prompt
        })
        
        # Send message to backend
        try:
            response = requests.post(
                "http://localhost:8000/chat",
                json={
                    "user_id": st.session_state.user_id,
                    "message": prompt,
                    "current_itinerary": st.session_state.current_itinerary
                }
            )
            
            if response.ok:
                response_data = response.json()
                
                # Add assistant response to chat history
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": response_data["response_message"],
                    "metadata": response_data.get("metadata", {})
                })
                
                # Update itinerary if present
                if "itinerary" in response_data:
                    st.session_state.current_itinerary = response_data["itinerary"]
                    
                st.rerun()
            else:
                st.error("Failed to get response from server")
        except Exception as e:
            st.error(f"Error communicating with server: {str(e)}")

def display_itinerary():
    if st.session_state.current_itinerary:
        st.subheader("Your Itinerary")
        itinerary = st.session_state.current_itinerary
        
        # Display basic information
        with st.container():
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.write(f"📍 City: {itinerary['city']}")
            with col2:
                st.write(f"📅 Date: {itinerary['date']}")
            with col3:
                st.write(f"💰 Budget: ${itinerary['budget']}")
            with col4:
                st.write(f"⏰ Duration: {itinerary['start_time']} - {itinerary['end_time']}")
        
        # Display map
        if 'stops' in itinerary and itinerary['stops']:
            display_map(itinerary['stops'])
        
        # Display stops
        for i, stop in enumerate(itinerary['stops'], 1):
            with st.expander(f"Stop {i}: {stop['location']['name']}", expanded=True):
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.write(f"📍 Location: {stop['location']['address']}")
                    st.write(f"⏰ Time: {stop['start_time']} - {stop['end_time']}")
                    if stop['travel_time_to_next']:
                        st.write(f"🚗 Travel to next: {stop['travel_time_to_next']} mins via {stop['travel_method_to_next']}")
                with col2:
                    st.write(f"💰 Cost: ${stop['cost']}")
                    st.write(f"Status: {stop['status']}")
        
        # Display total information
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"Total Cost: ${itinerary['total_cost']}")
        with col2:
            if st.button("Share Itinerary"):
                share_itinerary(itinerary)

def display_map(stops: List[Dict[str, Any]]):
    """Display a folium map with the itinerary stops."""
    # Create a map centered on the first stop
    first_stop = stops[0]['location']
    m = folium.Map(
        location=[first_stop['coordinates'][0], first_stop['coordinates'][1]],
        zoom_start=13
    )
    
    # Add markers for each stop
    for i, stop in enumerate(stops, 1):
        folium.Marker(
            location=[stop['location']['coordinates'][0], stop['location']['coordinates'][1]],
            popup=f"Stop {i}: {stop['location']['name']}",
            icon=folium.Icon(color='red', icon='info-sign')
        ).add_to(m)
    
    # Add lines connecting the stops
    coordinates = [[stop['location']['coordinates'][0], stop['location']['coordinates'][1]] 
                  for stop in stops]
    folium.PolyLine(
        coordinates,
        weight=2,
        color='blue',
        opacity=0.8
    ).add_to(m)
    
    # Display the map
    st_folium(m, width=700, height=500)

def share_itinerary(itinerary: Dict[str, Any]):
    """Generate a shareable version of the itinerary."""
    share_text = f"My {itinerary['city']} Itinerary for {itinerary['date']}\n\n"
    for i, stop in enumerate(itinerary['stops'], 1):
        share_text += f"{i}. {stop['location']['name']} ({stop['start_time']} - {stop['end_time']})\n"
    
    st.code(share_text, language=None)
    st.button("Copy to Clipboard", on_click=lambda: st.write("Copied!"))

def main():
    st.set_page_config(
        page_title="Tour Planner",
        page_icon="🗺️",
        layout="wide"
    )
    
    init_session_state()
    
    if not st.session_state.user_id:
        login_page()
    else:
        chat_interface()

if __name__ == "__main__":
    main()