"""YouTube Monitoring Page."""

import streamlit as st
import pandas as pd
from datetime import datetime
import time

st.set_page_config(page_title="YouTube Monitoring", page_icon="📺", layout="wide")

# Check authentication
if "token" not in st.session_state or "user" not in st.session_state:
    st.error("⚠️ Please login first")
    st.stop()

# Initialize API client
api_client = st.session_state.api_client

st.title("📺 YouTube Channel Monitoring")

# Check for active YouTube profile
success, profiles = api_client.list_profiles(platform="youtube")
has_active_profile = success and any(p.get("is_active") for p in profiles) if success else False

if not has_active_profile:
    st.warning("⚠️ No active YouTube API profile found. Please create one in the Profiles page first.")
    if st.button("Go to Profiles"):
        st.switch_page("pages/02_profiles.py")
    st.stop()

# Tabs
tab1, tab2, tab3 = st.tabs(["📋 Channels", "➕ Add Channels", "📊 Statistics"])

with tab1:
    st.subheader("Your YouTube Channels")

    # Control buttons
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        if st.button("▶️ Start All", use_container_width=True):
            with st.spinner("Starting monitoring..."):
                success, result = api_client.start_all_youtube_monitoring()
                if success:
                    st.success(f"✅ Started monitoring")
                    st.rerun()
                else:
                    st.error(f"Failed: {result}")

    with col2:
        if st.button("⏸️ Stop All", use_container_width=True):
            with st.spinner("Stopping monitoring..."):
                success, msg = api_client.stop_all_youtube_monitoring()
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
        success, channels = api_client.list_youtube_channels()

    if success and channels:
        # Display channels in a table-like format
        for channel in channels:
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 2])

                with col1:
                    status_icon = "🟢" if channel.get("is_monitoring") else "⚫"
                    st.markdown(f"### {status_icon} {channel['channel_name']}")
                    st.caption(f"Interval: {channel.get('monitoring_interval_seconds', 3600)}s | Videos: {channel.get('video_limit', 50)}")

                with col2:
                    st.metric("Videos", channel.get("total_videos", 0))

                with col3:
                    last_collected = channel.get("last_collected")
                    if last_collected:
                        st.caption(f"Last: {last_collected[:10]}")
                    else:
                        st.caption("Never collected")

                with col4:
                    if channel.get("is_monitoring"):
                        if st.button("⏸️ Stop", key=f"stop_{channel['id']}"):
                            success, msg = api_client.stop_youtube_monitoring(channel['id'])
                            if success:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                    else:
                        if st.button("▶️ Start", key=f"start_{channel['id']}"):
                            success, msg = api_client.start_youtube_monitoring(channel['id'])
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
                                success, msg = api_client.delete_youtube_channel(channel['id'])
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
                    with st.expander(f"Statistics for {channel['channel_name']}", expanded=True):
                        success_stats, stats = api_client.get_youtube_stats(channel['id'], days=30)

                        if success_stats and stats:
                            stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)

                            with stat_col1:
                                st.metric("Total Videos", stats.get("total_videos", 0))

                            with stat_col2:
                                st.metric("Total Views", f"{stats.get('total_views', 0):,}")

                            with stat_col3:
                                st.metric("Total Likes", f"{stats.get('total_likes', 0):,}")

                            with stat_col4:
                                st.metric("Avg Views/Video", f"{stats.get('avg_views_per_video', 0):,.0f}")

                            st.markdown("---")

                            stat_col5, stat_col6, stat_col7 = st.columns(3)

                            with stat_col5:
                                st.metric("Avg Likes/Video", f"{stats.get('avg_likes_per_video', 0):.1f}")

                            with stat_col6:
                                st.metric("Engagement Rate", f"{stats.get('avg_engagement_rate', 0):.2f}%")

                            with stat_col7:
                                st.metric("Total Comments", f"{stats.get('total_comments', 0):,}")

                            # Recent videos
                            if stats.get("recent_videos"):
                                st.markdown("### 🎥 Recent Videos")
                                for video in stats["recent_videos"][:5]:
                                    with st.container():
                                        video_title = video.get("title", "")
                                        # Truncate if too long
                                        if len(video_title) > 80:
                                            video_title = video_title[:80] + "..."

                                        st.markdown(f"**{video_title}**")
                                        video_col1, video_col2, video_col3 = st.columns(3)
                                        with video_col1:
                                            st.caption(f"👁️ {video.get('view_count', 0):,} views")
                                        with video_col2:
                                            st.caption(f"👍 {video.get('like_count', 0):,} likes")
                                        with video_col3:
                                            st.caption(f"💬 {video.get('comment_count', 0):,} comments")
                                        st.markdown("---")

                            # Top videos
                            if stats.get("most_viewed_video_id"):
                                st.markdown("### 🏆 Top Videos")
                                top_col1, top_col2 = st.columns(2)
                                with top_col1:
                                    st.markdown("**Most Viewed:**")
                                    title = stats.get("most_viewed_video_title", "Unknown")
                                    if len(title) > 50:
                                        title = title[:50] + "..."
                                    st.caption(title)
                                    st.metric("Views", f"{stats.get('most_viewed_video_views', 0):,}")
                                with top_col2:
                                    if stats.get("most_liked_video_id"):
                                        st.markdown("**Most Liked:**")
                                        title = stats.get("most_liked_video_title", "Unknown")
                                        if len(title) > 50:
                                            title = title[:50] + "..."
                                        st.caption(title)
                                        st.metric("Likes", f"{stats.get('most_liked_video_likes', 0):,}")
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
    st.subheader("Add YouTube Channels")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Single Channel")

        with st.form("add_single_channel"):
            channel_name = st.text_input(
                "Channel Name",
                placeholder="e.g., @MrBeast, @TechLinked, @NASA",
                help="Enter the YouTube channel name or handle"
            )

            interval = st.slider(
                "Monitoring Interval (seconds)",
                min_value=300,
                max_value=86400,
                value=3600,
                step=300,
                help="How often to collect videos (300-86400 seconds, default 1 hour)"
            )

            video_limit = st.slider(
                "Number of Videos to Track",
                min_value=1,
                max_value=200,
                value=50,
                step=10,
                help="How many recent videos to monitor"
            )

            submit = st.form_submit_button("Add Channel", use_container_width=True)

            if submit:
                if not channel_name:
                    st.error("Please enter a channel name")
                else:
                    with st.spinner("Adding channel..."):
                        success, result = api_client.create_youtube_channel(
                            channel_name, interval, video_limit
                        )

                        if success:
                            st.success(f"✅ Added channel: {channel_name}")
                            st.rerun()
                        else:
                            st.error(f"Failed to add channel: {result}")

    with col2:
        st.markdown("### Bulk Add")
        st.info("💡 Add multiple channels at once (one per line)")

        bulk_channels = st.text_area(
            "Channel Names",
            placeholder="@MrBeast\n@TechLinked\n@NASA\n@Veritasium",
            height=150,
            help="Enter one channel name per line"
        )

        bulk_interval = st.slider(
            "Monitoring Interval (bulk)",
            min_value=300,
            max_value=86400,
            value=3600,
            step=300,
            key="bulk_interval"
        )

        bulk_video_limit = st.slider(
            "Videos to Track (bulk)",
            min_value=1,
            max_value=200,
            value=50,
            step=10,
            key="bulk_video_limit"
        )

        if st.button("Add All Channels", use_container_width=True):
            channel_names = [c.strip() for c in bulk_channels.split('\n') if c.strip()]

            if not channel_names:
                st.error("Please enter at least one channel name")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()

                # Use bulk endpoint
                status_text.text(f"Adding {len(channel_names)} channels...")
                success, result = api_client.create_youtube_channels_bulk(
                    channel_names, bulk_interval, bulk_video_limit
                )

                progress_bar.progress(1.0)

                if success:
                    st.success(f"✅ Added {result.get('created_count', 0)} channel(s)")
                    if result.get('failed_count', 0) > 0:
                        st.warning(f"⚠️ {result['failed_count']} channel(s) failed")
                        for error in result.get('errors', []):
                            st.caption(f"❌ {error}")
                else:
                    st.error(f"Failed: {result}")

                progress_bar.empty()
                status_text.empty()

                if success and result.get('created_count', 0) > 0:
                    st.rerun()

with tab3:
    st.subheader("📊 Overall Statistics")

    # Load all channels for statistics
    success, channels = api_client.list_youtube_channels()

    if success and channels:
        total_channels = len(channels)
        monitoring_channels = sum(1 for c in channels if c.get("is_monitoring"))
        total_videos = sum(c.get("total_videos", 0) for c in channels)
        total_comments = sum(c.get("total_comments", 0) for c in channels)

        # Display overall metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Channels", total_channels)

        with col2:
            st.metric("Monitoring", monitoring_channels)

        with col3:
            st.metric("Total Videos", f"{total_videos:,}")

        with col4:
            st.metric("Total Comments", f"{total_comments:,}")

        st.markdown("---")

        # Channels table
        st.subheader("All Channels Overview")

        df_data = []
        for ch in channels:
            df_data.append({
                "Channel": ch['channel_name'],
                "Status": "🟢 Monitoring" if ch.get("is_monitoring") else "⚫ Idle",
                "Videos": ch.get("total_videos", 0),
                "Comments": ch.get("total_comments", 0),
                "Interval (s)": ch.get("monitoring_interval_seconds", 3600),
                "Video Limit": ch.get("video_limit", 50),
                "Last Collected": ch.get("last_collected", "Never")[:19] if ch.get("last_collected") else "Never"
            })

        if df_data:
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

    else:
        st.info("No channels to display statistics for")

st.markdown("---")
st.caption("💡 **Tip:** Background monitoring runs automatically. Videos and comments are collected even when this page is closed.")
