"""Twitch Monitoring Page."""

import streamlit as st
import pandas as pd
from datetime import datetime
import time

st.set_page_config(page_title="Twitch Monitoring", page_icon="🎮", layout="wide")

# Check authentication
if "token" not in st.session_state or "user" not in st.session_state:
    st.error("⚠️ Please login first")
    st.stop()

# Initialize API client
api_client = st.session_state.api_client

st.title("🎮 Twitch Stream Monitoring")

# Check for active Twitch profile
success, profiles = api_client.list_profiles(platform="twitch")
has_active_profile = success and any(p.get("is_active") for p in profiles) if success else False

if not has_active_profile:
    st.warning("⚠️ No active Twitch API profile found. Please create one in the Profiles page first.")
    if st.button("Go to Profiles"):
        st.switch_page("pages/02_profiles.py")
    st.stop()

# Tabs
tab1, tab2, tab3 = st.tabs(["📋 Channels", "➕ Add Channels", "📊 Statistics"])

with tab1:
    st.subheader("Your Twitch Channels")

    # Control buttons
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        if st.button("▶️ Start All", use_container_width=True):
            with st.spinner("Starting monitoring..."):
                success, result = api_client.start_all_monitoring()
                if success:
                    st.success(f"✅ Started monitoring")
                    st.rerun()
                else:
                    st.error(f"Failed: {result}")

    with col2:
        if st.button("⏸️ Stop All", use_container_width=True):
            with st.spinner("Stopping monitoring..."):
                success, msg = api_client.stop_all_monitoring()
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error("Failed to stop monitoring")

    with col3:
        auto_refresh = st.checkbox("Auto-refresh (every 10 sec)", key="auto_refresh")

    st.markdown("---")

    # Load channels
    with st.spinner("Loading channels..."):
        success, channels = api_client.list_twitch_channels()

    if success and channels:
        # Display channels in a table-like format
        for channel in channels:
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 2])

                with col1:
                    status_icon = "🟢" if channel.get("is_monitoring") else "⚫"
                    st.markdown(f"### {status_icon} {channel['username']}")
                    st.caption(f"Interval: {channel.get('monitoring_interval_seconds', 30)}s")

                with col2:
                    st.metric("Records", channel.get("total_records", 0))

                with col3:
                    last_checked = channel.get("last_checked")
                    if last_checked:
                        st.caption(f"Last: {last_checked[:10]}")
                    else:
                        st.caption("Never checked")

                with col4:
                    if channel.get("is_monitoring"):
                        if st.button("⏸️ Stop", key=f"stop_{channel['id']}"):
                            success, msg = api_client.stop_monitoring(channel['id'])
                            if success:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                    else:
                        if st.button("▶️ Start", key=f"start_{channel['id']}"):
                            success, msg = api_client.start_monitoring(channel['id'])
                            if success:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)

                with col5:
                    subcol1, subcol2 = st.columns(2)

                    with subcol1:
                        if st.button("📊 Stats", key=f"stats_{channel['id']}"):
                            st.session_state[f"show_stats_{channel['id']}"] = True

                    with subcol2:
                        if st.button("🗑️", key=f"delete_{channel['id']}"):
                            if st.session_state.get(f"confirm_delete_{channel['id']}", False):
                                success, msg = api_client.delete_twitch_channel(channel['id'])
                                if success:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                            else:
                                st.session_state[f"confirm_delete_{channel['id']}"] = True
                                st.warning("Click again to confirm")

                # Show stats if requested
                if st.session_state.get(f"show_stats_{channel['id']}", False):
                    with st.expander(f"Statistics for {channel['username']}", expanded=True):
                        success_stats, stats = api_client.get_twitch_stats(channel['id'])

                        if success_stats and stats:
                            stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)

                            with stat_col1:
                                st.metric("Total Records", stats.get("total_records", 0))

                            with stat_col2:
                                st.metric("Live Sessions", stats.get("total_live_sessions", 0))

                            with stat_col3:
                                st.metric("Avg Viewers", stats.get("average_viewers", 0))

                            with stat_col4:
                                st.metric("Peak Viewers", stats.get("peak_viewers", 0))

                            if stats.get("is_currently_live"):
                                st.success(f"🔴 Currently LIVE with {stats.get('current_viewers', 0)} viewers")
                                if stats.get("current_game"):
                                    st.info(f"Playing: {stats['current_game']}")
                            else:
                                st.info("⚫ Currently Offline")
                        else:
                            st.warning("No statistics available yet")

                        if st.button("Close Stats", key=f"close_stats_{channel['id']}"):
                            st.session_state[f"show_stats_{channel['id']}"] = False
                            st.rerun()

                st.markdown("---")

        # Auto-refresh logic
        if auto_refresh:
            time.sleep(10)
            st.rerun()

    elif success:
        st.info("📭 No channels added yet. Use the 'Add Channels' tab to get started.")
    else:
        st.error(f"Failed to load channels: {channels}")

with tab2:
    st.subheader("Add Twitch Channels")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Single Channel")

        with st.form("add_single_channel"):
            username = st.text_input(
                "Twitch Username",
                placeholder="e.g., ninja, shroud, pokimane",
                help="Enter the Twitch username (without @)"
            )

            interval = st.slider(
                "Monitoring Interval (seconds)",
                min_value=10,
                max_value=300,
                value=30,
                step=10,
                help="How often to check the stream status"
            )

            submit = st.form_submit_button("Add Channel", use_container_width=True)

            if submit:
                if not username:
                    st.error("Please enter a username")
                else:
                    with st.spinner("Adding channel..."):
                        success, result = api_client.create_twitch_channel(username, interval)

                        if success:
                            st.success(f"✅ Added channel: {username}")
                            st.rerun()
                        else:
                            st.error(f"Failed to add channel: {result}")

    with col2:
        st.markdown("### Bulk Add")
        st.info("💡 Add multiple channels at once (one per line)")

        bulk_usernames = st.text_area(
            "Usernames",
            placeholder="ninja\nshroud\npokimane\nxqc",
            height=150,
            help="Enter one username per line"
        )

        bulk_interval = st.slider(
            "Monitoring Interval (bulk)",
            min_value=10,
            max_value=300,
            value=30,
            step=10,
            key="bulk_interval"
        )

        if st.button("Add All Channels", use_container_width=True):
            usernames = [u.strip() for u in bulk_usernames.split('\n') if u.strip()]

            if not usernames:
                st.error("Please enter at least one username")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()

                success_count = 0
                failed_count = 0

                for i, username in enumerate(usernames):
                    status_text.text(f"Adding {username}...")
                    success, result = api_client.create_twitch_channel(username, bulk_interval)

                    if success:
                        success_count += 1
                    else:
                        failed_count += 1
                        st.warning(f"Failed to add {username}: {result}")

                    progress_bar.progress((i + 1) / len(usernames))

                progress_bar.empty()
                status_text.empty()

                st.success(f"✅ Added {success_count} channel(s)")
                if failed_count > 0:
                    st.warning(f"⚠️ {failed_count} channel(s) failed")

                st.rerun()

with tab3:
    st.subheader("📊 Overall Statistics")

    # Load all channels for statistics
    success, channels = api_client.list_twitch_channels()

    if success and channels:
        total_channels = len(channels)
        monitoring_channels = sum(1 for c in channels if c.get("is_monitoring"))
        total_records = sum(c.get("total_records", 0) for c in channels)

        # Display overall metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Channels", total_channels)

        with col2:
            st.metric("Monitoring", monitoring_channels)

        with col3:
            st.metric("Total Records", total_records)

        with col4:
            avg_records = total_records / total_channels if total_channels > 0 else 0
            st.metric("Avg Records/Channel", f"{avg_records:.0f}")

        st.markdown("---")

        # Channels table
        st.subheader("All Channels Overview")

        df_data = []
        for ch in channels:
            df_data.append({
                "Username": ch["username"],
                "Status": "🟢 Monitoring" if ch.get("is_monitoring") else "⚫ Idle",
                "Records": ch.get("total_records", 0),
                "Interval (s)": ch.get("monitoring_interval_seconds", 30),
                "Last Checked": ch.get("last_checked", "Never")[:19] if ch.get("last_checked") else "Never"
            })

        if df_data:
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

    else:
        st.info("No channels to display statistics for")

st.markdown("---")
st.caption("💡 **Tip:** Background monitoring runs automatically. Data is collected even when this page is closed.")
