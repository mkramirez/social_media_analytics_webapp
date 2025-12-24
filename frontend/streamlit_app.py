"""Social Media Analytics Platform - Streamlit Frontend."""

import streamlit as st
from components.api_client import APIClient

# Page configuration
st.set_page_config(
    page_title="Social Media Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize API client
if "api_client" not in st.session_state:
    st.session_state.api_client = APIClient()


def show_login_page():
    """Display login page."""
    st.title("🔐 Social Media Analytics Platform")
    st.subheader("Login to Your Account")

    # Check API health
    if not st.session_state.api_client.health_check():
        st.error("⚠️ Cannot connect to backend API. Please make sure the server is running at http://localhost:8000")
        st.info("To start the backend: `cd backend && python -m uvicorn app.main:app --reload`")
        return

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("---")

        # Login form
        with st.form("login_form"):
            username = st.text_input("Username or Email", placeholder="Enter your username or email")
            password = st.text_input("Password", type="password", placeholder="Enter your password")

            col_login, col_register = st.columns(2)

            with col_login:
                submit_button = st.form_submit_button("Login", use_container_width=True)

            with col_register:
                register_button = st.form_submit_button("Create Account", use_container_width=True)

            if submit_button:
                if not username or not password:
                    st.error("Please enter both username and password")
                else:
                    with st.spinner("Logging in..."):
                        success, result = st.session_state.api_client.login(username, password)

                        if success:
                            # Store token and user info
                            st.session_state.token = result["access_token"]
                            st.session_state.user = result["user"]
                            st.success(f"Welcome back, {result['user']['username']}!")
                            st.rerun()
                        else:
                            st.error(f"Login failed: {result}")

            if register_button:
                st.session_state.show_register = True
                st.rerun()


def show_register_page():
    """Display registration page."""
    st.title("📝 Create Your Account")
    st.subheader("Join Social Media Analytics Platform")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("---")

        # Registration form
        with st.form("register_form"):
            email = st.text_input("Email", placeholder="your.email@example.com")
            username = st.text_input("Username", placeholder="Choose a username (3-50 characters)")
            full_name = st.text_input("Full Name (Optional)", placeholder="Your full name")
            password = st.text_input("Password", type="password", placeholder="Create a strong password")
            password_confirm = st.text_input("Confirm Password", type="password", placeholder="Re-enter your password")

            # Password requirements
            st.info("""
            **Password Requirements:**
            - At least 8 characters
            - One uppercase letter
            - One lowercase letter
            - One digit
            - One special character (!@#$%^&*()_+-=[]{}|;:,.<>?)
            """)

            col_submit, col_back = st.columns(2)

            with col_submit:
                submit_button = st.form_submit_button("Register", use_container_width=True)

            with col_back:
                back_button = st.form_submit_button("Back to Login", use_container_width=True)

            if submit_button:
                # Validation
                if not all([email, username, password, password_confirm]):
                    st.error("Please fill in all required fields")
                elif password != password_confirm:
                    st.error("Passwords do not match")
                elif len(password) < 8:
                    st.error("Password must be at least 8 characters")
                else:
                    with st.spinner("Creating account..."):
                        success, result = st.session_state.api_client.register(
                            email=email,
                            username=username,
                            password=password,
                            full_name=full_name if full_name else None
                        )

                        if success:
                            # Auto-login after registration
                            st.session_state.token = result["access_token"]
                            st.session_state.user = result["user"]
                            st.success(f"Account created! Welcome, {result['user']['username']}!")
                            st.session_state.show_register = False
                            st.rerun()
                        else:
                            st.error(f"Registration failed: {result}")

            if back_button:
                st.session_state.show_register = False
                st.rerun()


def show_main_app():
    """Display main application after login."""
    # Sidebar
    with st.sidebar:
        st.title("📊 Social Media Analytics")

        # User info
        if "user" in st.session_state:
            st.write(f"👤 **{st.session_state.user['username']}**")
            st.write(f"📧 {st.session_state.user['email']}")

        st.markdown("---")

        # Navigation
        st.subheader("Navigation")
        page = st.radio(
            "Go to",
            ["🏠 Home", "👤 Profile", "🎮 Twitch", "🐦 Twitter", "▶️ YouTube", "🤖 Reddit", "📊 Analytics", "📤 Export", "⚙️ Settings"],
            label_visibility="collapsed"
        )

        st.markdown("---")

        # Logout button
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.api_client.logout()
            # Clear session
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # Main content area
    st.title("Welcome to Social Media Analytics Platform! 🎉")

    st.markdown("""
    ### 🚀 Getting Started

    Your account is successfully set up! This is the **Phase 1** version of the web application.

    #### ✅ What's Working Now:
    - **User Authentication** - Register, login, logout
    - **Secure Sessions** - JWT token-based authentication
    - **Multi-user Support** - Each user has isolated data

    #### 🔨 Coming in Phase 2:
    - **Platform Monitoring** - Twitch, Twitter, YouTube, Reddit
    - **Background Jobs** - APScheduler for continuous monitoring
    - **Analytics Dashboard** - Sentiment, engagement, trends
    - **Data Export** - CSV and PDF reports
    - **Real-time Updates** - WebSocket support

    #### 📊 Current Status:
    - ✅ Backend API running
    - ✅ Database connected
    - ✅ Authentication working
    - ⏳ Platform integrations (coming next)

    ---

    ### 🛠️ Development Progress

    **Phase 1: Foundation** ✅ COMPLETE
    - User registration and login
    - JWT authentication
    - PostgreSQL database
    - FastAPI backend

    **Phase 2: Twitch Integration** 🔄 NEXT
    - Channel monitoring
    - Stream data collection
    - Background jobs

    Select a page from the sidebar to get started (features will be added in upcoming phases)!
    """)

    # Show some stats
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Account Status", "Active ✅")

    with col2:
        st.metric("API Status", "Connected ✅" if st.session_state.api_client.health_check() else "Offline ❌")

    with col3:
        st.metric("Phase", "1 of 8")


def main():
    """Main application entry point."""
    # Initialize session state
    if "show_register" not in st.session_state:
        st.session_state.show_register = False

    # Check if user is logged in
    if "token" in st.session_state and "user" in st.session_state:
        # Verify token is still valid
        if st.session_state.api_client.verify_token():
            show_main_app()
        else:
            # Token expired, clear session
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    else:
        # Show login or register page
        if st.session_state.show_register:
            show_register_page()
        else:
            show_login_page()


if __name__ == "__main__":
    main()
