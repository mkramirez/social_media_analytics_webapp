"""Profile Management Page - API Credential Setup."""

import streamlit as st
from components.api_client import APIClient

st.set_page_config(page_title="Profile Management", page_icon="👤", layout="wide")

# Check authentication
if "token" not in st.session_state or "user" not in st.session_state:
    st.error("⚠️ Please login first")
    st.stop()

# Initialize API client
api_client = st.session_state.api_client

st.title("👤 API Profile Management")
st.markdown("Configure your API credentials for each platform")

# Tabs for different actions
tab1, tab2 = st.tabs(["📋 My Profiles", "➕ Create New Profile"])

with tab1:
    st.subheader("Your API Profiles")

    # Platform filter
    platform_filter = st.selectbox(
        "Filter by Platform",
        ["All", "Twitch", "Twitter", "YouTube", "Reddit"]
    )

    with st.spinner("Loading profiles..."):
        success, profiles = api_client.list_profiles(
            platform=None if platform_filter == "All" else platform_filter.lower()
        )

    if success:
        if not profiles:
            st.info("📭 No profiles found. Create your first profile using the 'Create New Profile' tab.")
        else:
            for profile in profiles:
                with st.expander(f"🔑 {profile['profile_name']} ({profile['platform'].title()})", expanded=False):
                    col1, col2, col3 = st.columns([2, 1, 1])

                    with col1:
                        st.write(f"**Platform:** {profile['platform'].title()}")
                        st.write(f"**Status:** {'✅ Active' if profile['is_active'] else '❌ Inactive'}")
                        st.write(f"**Created:** {profile['created_at'][:10]}")

                    with col2:
                        if st.button("🗑️ Delete", key=f"delete_{profile['id']}"):
                            if st.session_state.get(f"confirm_delete_{profile['id']}", False):
                                success_del, msg = api_client.delete_profile(profile['id'])
                                if success_del:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(f"Delete failed: {msg}")
                            else:
                                st.session_state[f"confirm_delete_{profile['id']}"] = True
                                st.warning("Click again to confirm deletion")

                    with col3:
                        if st.button("🔄 Toggle Status", key=f"toggle_{profile['id']}"):
                            success_upd, msg = api_client.update_profile(
                                profile['id'],
                                {"is_active": not profile['is_active']}
                            )
                            if success_upd:
                                st.success("Status updated!")
                                st.rerun()
                            else:
                                st.error(f"Update failed: {msg}")
    else:
        st.error(f"Failed to load profiles: {profiles}")

with tab2:
    st.subheader("Create New API Profile")

    with st.form("create_profile"):
        profile_name = st.text_input(
            "Profile Name",
            placeholder="e.g., My Twitch Account",
            help="Give this profile a descriptive name"
        )

        platform = st.selectbox(
            "Platform",
            ["Twitch", "Twitter", "YouTube", "Reddit"]
        )

        st.markdown("---")
        st.markdown(f"### {platform} API Credentials")

        if platform == "Twitch":
            st.info("""
            **How to get Twitch API credentials:**
            1. Go to https://dev.twitch.tv/console
            2. Register your application
            3. Copy Client ID and Client Secret
            """)

            client_id = st.text_input("Client ID")
            client_secret = st.text_input("Client Secret", type="password")

            credentials = {
                "client_id": client_id,
                "client_secret": client_secret
            }

        elif platform == "Twitter":
            st.info("""
            **How to get Twitter API credentials:**
            1. Go to https://developer.twitter.com
            2. Create a project and app
            3. Generate Bearer Token
            """)

            bearer_token = st.text_input("Bearer Token", type="password")

            credentials = {
                "bearer_token": bearer_token
            }

        elif platform == "YouTube":
            st.info("""
            **How to get YouTube API credentials:**
            1. Go to https://console.cloud.google.com
            2. Enable YouTube Data API v3
            3. Create API Key
            """)

            api_key = st.text_input("API Key", type="password")

            credentials = {
                "api_key": api_key
            }

        else:  # Reddit
            st.info("""
            **How to get Reddit API credentials:**
            1. Go to https://www.reddit.com/prefs/apps
            2. Create a new app (script type)
            3. Copy Client ID, Client Secret, and create User Agent
            """)

            client_id_reddit = st.text_input("Client ID")
            client_secret_reddit = st.text_input("Client Secret", type="password")
            user_agent = st.text_input("User Agent", placeholder="MyApp/1.0")

            credentials = {
                "client_id": client_id_reddit,
                "client_secret": client_secret_reddit,
                "user_agent": user_agent
            }

        submit = st.form_submit_button("Create Profile", use_container_width=True)

        if submit:
            if not profile_name:
                st.error("Please enter a profile name")
            elif not all(credentials.values()):
                st.error("Please fill in all credential fields")
            else:
                with st.spinner("Creating profile..."):
                    success, result = api_client.create_profile(
                        profile_name=profile_name,
                        platform=platform.lower(),
                        credentials=credentials
                    )

                    if success:
                        st.success(f"✅ Profile '{profile_name}' created successfully!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(f"Failed to create profile: {result}")

st.markdown("---")
st.caption("💡 **Tip:** Credentials are encrypted before storage for security.")
