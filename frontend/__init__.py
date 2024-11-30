from .app import main

__version__ = "1.0.0"

def run_app():
    """Run the Streamlit frontend application."""
    main()

# Export only what's needed
__all__ = ['main', 'run_app']

# Optional: Add any frontend-specific configuration
STREAMLIT_CONFIG = {
    'page_title': 'Tour Planner',
    'page_icon': '🗺️',
    'layout': 'wide',
    'initial_sidebar_state': 'expanded'
}

# Optional: Add any frontend utility functions
def clear_session():
    """Clear all session state variables."""
    try:
        from streamlit import session_state
        for key in list(session_state.keys()):
            del session_state[key]
    except Exception as e:
        print(f"Error clearing session: {str(e)}")