"""Twitter Monitoring Page."""

import streamlit as st
import pandas as pd
from datetime import datetime
import time

st.set_page_config(page_title="Twitter Monitoring", page_icon="🐦", layout="wide")

# Check authentication
if "token" not in st.session_state or "user" not in st.session_state:
    st.error("⚠️ Please login first")
    st.stop()

# Initialize API client
api_client = st.session_state.api_client

st.title("🐦 Twitter User Monitoring")

# Check for active Twitter profile
success, profiles = api_client.list_profiles(platform="twitter")
has_active_profile = success and any(p.get("is_active") for p in profiles) if success else False

if not has_active_profile:
    st.warning("⚠️ No active Twitter API profile found. Please create one in the Profiles page first.")
    if st.button("Go to Profiles"):
        st.switch_page("pages/02_profiles.py")
    st.stop()

# Tabs
tab1, tab2, tab3 = st.tabs(["📋 Users", "➕ Add Users", "📊 Statistics"])

with tab1:
    st.subheader("Your Twitter Users")

    # Control buttons
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        if st.button("▶️ Start All", use_container_width=True):
            with st.spinner("Starting monitoring..."):
                success, result = api_client.start_all_twitter_monitoring()
                if success:
                    st.success(f"✅ Started monitoring")
                    st.rerun()
                else:
                    st.error(f"Failed: {result}")

    with col2:
        if st.button("⏸️ Stop All", use_container_width=True):
            with st.spinner("Stopping monitoring..."):
                success, msg = api_client.stop_all_twitter_monitoring()
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error("Failed to stop monitoring")

    with col3:
        auto_refresh = st.checkbox("Auto-refresh (every 10 sec)", key="auto_refresh")

    st.markdown("---")

    # Load users
    with st.spinner("Loading users..."):
        success, users = api_client.list_twitter_users()

    if success and users:
        # Display users in a table-like format
        for user in users:
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 2])

                with col1:
                    status_icon = "🟢" if user.get("is_monitoring") else "⚫"
                    st.markdown(f"### {status_icon} @{user['username']}")
                    st.caption(f"Interval: {user.get('monitoring_interval_seconds', 300)}s | Days: {user.get('days_to_collect', 7)}d")

                with col2:
                    st.metric("Tweets", user.get("total_tweets", 0))

                with col3:
                    last_collected = user.get("last_collected")
                    if last_collected:
                        st.caption(f"Last: {last_collected[:10]}")
                    else:
                        st.caption("Never collected")

                with col4:
                    if user.get("is_monitoring"):
                        if st.button("⏸️ Stop", key=f"stop_{user['id']}"):
                            success, msg = api_client.stop_twitter_monitoring(user['id'])
                            if success:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                    else:
                        if st.button("▶️ Start", key=f"start_{user['id']}"):
                            success, msg = api_client.start_twitter_monitoring(user['id'])
                            if success:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)

                with col5:
                    subcol1, subcol2 = st.columns(2)

                    with subcol1:
                        if st.button("📊 Stats", key=f"stats_{user['id']}"):
                            st.session_state[f"show_stats_{user['id']}"] = True

                    with subcol2:
                        if st.button("🗑️", key=f"delete_{user['id']}"):
                            if st.session_state.get(f"confirm_delete_{user['id']}", False):
                                success, msg = api_client.delete_twitter_user(user['id'])
                                if success:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                            else:
                                st.session_state[f"confirm_delete_{user['id']}"] = True
                                st.warning("Click again to confirm")

                # Show stats if requested
                if st.session_state.get(f"show_stats_{user['id']}", False):
                    with st.expander(f"Statistics for @{user['username']}", expanded=True):
                        success_stats, stats = api_client.get_twitter_stats(user['id'], days=30)

                        if success_stats and stats:
                            stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)

                            with stat_col1:
                                st.metric("Total Tweets", stats.get("total_tweets", 0))

                            with stat_col2:
                                st.metric("Total Likes", f"{stats.get('total_likes', 0):,}")

                            with stat_col3:
                                st.metric("Total Retweets", f"{stats.get('total_retweets', 0):,}")

                            with stat_col4:
                                st.metric("Avg Likes/Tweet", f"{stats.get('avg_likes_per_tweet', 0):.1f}")

                            st.markdown("---")

                            stat_col5, stat_col6, stat_col7 = st.columns(3)

                            with stat_col5:
                                st.metric("Avg Retweets/Tweet", f"{stats.get('avg_retweets_per_tweet', 0):.1f}")

                            with stat_col6:
                                st.metric("Engagement Rate", f"{stats.get('avg_engagement_rate', 0):.2f}%")

                            with stat_col7:
                                st.metric("Total Impressions", f"{stats.get('total_impressions', 0):,}")

                            # Recent tweets
                            if stats.get("recent_tweets"):
                                st.markdown("### 📝 Recent Tweets")
                                for tweet in stats["recent_tweets"][:5]:
                                    with st.container():
                                        tweet_text = tweet.get("text", "")
                                        # Truncate if too long
                                        if len(tweet_text) > 100:
                                            tweet_text = tweet_text[:100] + "..."

                                        st.markdown(f"**{tweet_text}**")
                                        tweet_col1, tweet_col2, tweet_col3 = st.columns(3)
                                        with tweet_col1:
                                            st.caption(f"❤️ {tweet.get('like_count', 0)}")
                                        with tweet_col2:
                                            st.caption(f"🔄 {tweet.get('retweet_count', 0)}")
                                        with tweet_col3:
                                            st.caption(f"💬 {tweet.get('reply_count', 0)}")
                                        st.markdown("---")
                        else:
                            st.warning("No statistics available yet")

                        if st.button("Close Stats", key=f"close_stats_{user['id']}"):
                            st.session_state[f"show_stats_{user['id']}"] = False
                            st.rerun()

                st.markdown("---")

        # Auto-refresh logic
        if auto_refresh:
            time.sleep(10)
            st.rerun()

    elif success:
        st.info("📭 No users added yet. Use the 'Add Users' tab to get started.")
    else:
        st.error(f"Failed to load users: {users}")

with tab2:
    st.subheader("Add Twitter Users")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Single User")

        with st.form("add_single_user"):
            username = st.text_input(
                "Twitter Username",
                placeholder="e.g., elonmusk, openai, anthropicai",
                help="Enter the Twitter username (without @)"
            )

            interval = st.slider(
                "Monitoring Interval (seconds)",
                min_value=60,
                max_value=3600,
                value=300,
                step=60,
                help="How often to collect tweets (60-3600 seconds)"
            )

            days_to_collect = st.slider(
                "Days of Tweets to Collect",
                min_value=1,
                max_value=30,
                value=7,
                step=1,
                help="How many days back to collect tweets"
            )

            submit = st.form_submit_button("Add User", use_container_width=True)

            if submit:
                if not username:
                    st.error("Please enter a username")
                else:
                    with st.spinner("Adding user..."):
                        success, result = api_client.create_twitter_user(
                            username, interval, days_to_collect
                        )

                        if success:
                            st.success(f"✅ Added user: @{username}")
                            st.rerun()
                        else:
                            st.error(f"Failed to add user: {result}")

    with col2:
        st.markdown("### Bulk Add")
        st.info("💡 Add multiple users at once (one per line)")

        bulk_usernames = st.text_area(
            "Usernames",
            placeholder="elonmusk\nopenai\nanthropicai\ngoogleai",
            height=150,
            help="Enter one username per line"
        )

        bulk_interval = st.slider(
            "Monitoring Interval (bulk)",
            min_value=60,
            max_value=3600,
            value=300,
            step=60,
            key="bulk_interval"
        )

        bulk_days = st.slider(
            "Days to Collect (bulk)",
            min_value=1,
            max_value=30,
            value=7,
            step=1,
            key="bulk_days"
        )

        if st.button("Add All Users", use_container_width=True):
            usernames = [u.strip() for u in bulk_usernames.split('\n') if u.strip()]

            if not usernames:
                st.error("Please enter at least one username")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()

                # Use bulk endpoint
                status_text.text(f"Adding {len(usernames)} users...")
                success, result = api_client.create_twitter_users_bulk(
                    usernames, bulk_interval, bulk_days
                )

                progress_bar.progress(1.0)

                if success:
                    st.success(f"✅ Added {result.get('created_count', 0)} user(s)")
                    if result.get('failed_count', 0) > 0:
                        st.warning(f"⚠️ {result['failed_count']} user(s) failed")
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

    # Load all users for statistics
    success, users = api_client.list_twitter_users()

    if success and users:
        total_users = len(users)
        monitoring_users = sum(1 for u in users if u.get("is_monitoring"))
        total_tweets = sum(u.get("total_tweets", 0) for u in users)

        # Display overall metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Users", total_users)

        with col2:
            st.metric("Monitoring", monitoring_users)

        with col3:
            st.metric("Total Tweets", f"{total_tweets:,}")

        with col4:
            avg_tweets = total_tweets / total_users if total_users > 0 else 0
            st.metric("Avg Tweets/User", f"{avg_tweets:.0f}")

        st.markdown("---")

        # Users table
        st.subheader("All Users Overview")

        df_data = []
        for u in users:
            df_data.append({
                "Username": f"@{u['username']}",
                "Status": "🟢 Monitoring" if u.get("is_monitoring") else "⚫ Idle",
                "Tweets": u.get("total_tweets", 0),
                "Interval (s)": u.get("monitoring_interval_seconds", 300),
                "Days to Collect": u.get("days_to_collect", 7),
                "Last Collected": u.get("last_collected", "Never")[:19] if u.get("last_collected") else "Never"
            })

        if df_data:
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

    else:
        st.info("No users to display statistics for")

st.markdown("---")
st.caption("💡 **Tip:** Background monitoring runs automatically. Tweets are collected even when this page is closed.")
