"""Reddit Monitoring Page."""

import streamlit as st
import pandas as pd
from datetime import datetime
import time

st.set_page_config(page_title="Reddit Monitoring", page_icon="🤖", layout="wide")

# Check authentication
if "token" not in st.session_state or "user" not in st.session_state:
    st.error("⚠️ Please login first")
    st.stop()

# Initialize API client
api_client = st.session_state.api_client

st.title("🤖 Reddit Subreddit Monitoring")

# Check for active Reddit profile
success, profiles = api_client.list_profiles(platform="reddit")
has_active_profile = success and any(p.get("is_active") for p in profiles) if success else False

if not has_active_profile:
    st.warning("⚠️ No active Reddit API profile found. Please create one in the Profiles page first.")
    if st.button("Go to Profiles"):
        st.switch_page("pages/02_profiles.py")
    st.stop()

# Tabs
tab1, tab2, tab3 = st.tabs(["📋 Subreddits", "➕ Add Subreddits", "📊 Statistics"])

with tab1:
    st.subheader("Your Reddit Subreddits")

    # Control buttons
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        if st.button("▶️ Start All", use_container_width=True):
            with st.spinner("Starting monitoring..."):
                success, result = api_client.start_all_reddit_monitoring()
                if success:
                    st.success(f"✅ Started monitoring")
                    st.rerun()
                else:
                    st.error(f"Failed: {result}")

    with col2:
        if st.button("⏸️ Stop All", use_container_width=True):
            with st.spinner("Stopping monitoring..."):
                success, msg = api_client.stop_all_reddit_monitoring()
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error("Failed to stop monitoring")

    with col3:
        auto_refresh = st.checkbox("Auto-refresh (every 10 sec)", key="auto_refresh")

    st.markdown("---")

    # Load subreddits
    with st.spinner("Loading subreddits..."):
        success, subreddits = api_client.list_reddit_subreddits()

    if success and subreddits:
        # Display subreddits in a table-like format
        for subreddit in subreddits:
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 2])

                with col1:
                    status_icon = "🟢" if subreddit.get("is_monitoring") else "⚫"
                    st.markdown(f"### {status_icon} r/{subreddit['subreddit_name']}")
                    st.caption(f"Interval: {subreddit.get('monitoring_interval_seconds', 1800)}s | Posts: {subreddit.get('post_limit', 100)} | Comments: {subreddit.get('comment_limit', 50)}")

                with col2:
                    st.metric("Posts", subreddit.get("total_posts", 0))

                with col3:
                    last_collected = subreddit.get("last_collected")
                    if last_collected:
                        st.caption(f"Last: {last_collected[:10]}")
                    else:
                        st.caption("Never collected")

                with col4:
                    if subreddit.get("is_monitoring"):
                        if st.button("⏸️ Stop", key=f"stop_{subreddit['id']}"):
                            success, msg = api_client.stop_reddit_monitoring(subreddit['id'])
                            if success:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                    else:
                        if st.button("▶️ Start", key=f"start_{subreddit['id']}"):
                            success, msg = api_client.start_reddit_monitoring(subreddit['id'])
                            if success:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)

                with col5:
                    subcol1, subcol2 = st.columns(2)

                    with subcol1:
                        if st.button("📊 Stats", key=f"stats_{subreddit['id']}"):
                            st.session_state[f"show_stats_{subreddit['id']}"] = True

                    with subcol2:
                        if st.button("🗑️", key=f"delete_{subreddit['id']}"):
                            if st.session_state.get(f"confirm_delete_{subreddit['id']}", False):
                                success, msg = api_client.delete_reddit_subreddit(subreddit['id'])
                                if success:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                            else:
                                st.session_state[f"confirm_delete_{subreddit['id']}"] = True
                                st.warning("Click again to confirm")

                # Show stats if requested
                if st.session_state.get(f"show_stats_{subreddit['id']}", False):
                    with st.expander(f"Statistics for r/{subreddit['subreddit_name']}", expanded=True):
                        success_stats, stats = api_client.get_reddit_stats(subreddit['id'], days=7)

                        if success_stats and stats:
                            stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)

                            with stat_col1:
                                st.metric("Total Posts", stats.get("total_posts", 0))

                            with stat_col2:
                                st.metric("Total Upvotes", f"{stats.get('total_upvotes', 0):,}")

                            with stat_col3:
                                st.metric("Total Comments", f"{stats.get('total_comments', 0):,}")

                            with stat_col4:
                                st.metric("Avg Upvotes/Post", f"{stats.get('avg_upvotes_per_post', 0):.1f}")

                            st.markdown("---")

                            stat_col5, stat_col6 = st.columns(2)

                            with stat_col5:
                                st.metric("Avg Comments/Post", f"{stats.get('avg_comments_per_post', 0):.1f}")

                            with stat_col6:
                                st.metric("Avg Upvote Ratio", f"{stats.get('avg_upvote_ratio', 0):.2f}")

                            # Top posts
                            if stats.get("most_upvoted_post_id"):
                                st.markdown("### 🏆 Top Posts")
                                top_col1, top_col2 = st.columns(2)
                                with top_col1:
                                    st.markdown("**Most Upvoted:**")
                                    title = stats.get("most_upvoted_post_title", "Unknown")
                                    if len(title) > 60:
                                        title = title[:60] + "..."
                                    st.caption(title)
                                    st.metric("Upvotes", f"{stats.get('most_upvoted_post_upvotes', 0):,}")
                                with top_col2:
                                    if stats.get("most_commented_post_id"):
                                        st.markdown("**Most Commented:**")
                                        title = stats.get("most_commented_post_title", "Unknown")
                                        if len(title) > 60:
                                            title = title[:60] + "..."
                                        st.caption(title)
                                        st.metric("Comments", f"{stats.get('most_commented_post_comments', 0):,}")

                            # Recent posts
                            if stats.get("recent_posts"):
                                st.markdown("### 📝 Recent Posts")
                                for post in stats["recent_posts"][:5]:
                                    with st.container():
                                        post_title = post.get("title", "")
                                        # Truncate if too long
                                        if len(post_title) > 80:
                                            post_title = post_title[:80] + "..."

                                        st.markdown(f"**{post_title}**")
                                        post_col1, post_col2, post_col3 = st.columns(3)
                                        with post_col1:
                                            st.caption(f"⬆️ {post.get('upvotes', 0):,} upvotes")
                                        with post_col2:
                                            st.caption(f"💬 {post.get('num_comments', 0):,} comments")
                                        with post_col3:
                                            ratio = post.get('upvote_ratio', 0.0)
                                            st.caption(f"📊 {ratio:.0%} upvote ratio")
                                        st.markdown("---")
                        else:
                            st.warning("No statistics available yet")

                        if st.button("Close Stats", key=f"close_stats_{subreddit['id']}"):
                            st.session_state[f"show_stats_{subreddit['id']}"] = False
                            st.rerun()

                st.markdown("---")

        # Auto-refresh logic
        if auto_refresh:
            time.sleep(10)
            st.rerun()

    elif success:
        st.info("📭 No subreddits added yet. Use the 'Add Subreddits' tab to get started.")
    else:
        st.error(f"Failed to load subreddits: {subreddits}")

with tab2:
    st.subheader("Add Reddit Subreddits")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Single Subreddit")

        with st.form("add_single_subreddit"):
            subreddit_name = st.text_input(
                "Subreddit Name",
                placeholder="e.g., python, MachineLearning, datascience",
                help="Enter the subreddit name (without r/)"
            )

            interval = st.slider(
                "Monitoring Interval (seconds)",
                min_value=600,
                max_value=86400,
                value=1800,
                step=300,
                help="How often to collect posts (600-86400 seconds, default 30 minutes)"
            )

            post_limit = st.slider(
                "Number of Posts to Track",
                min_value=1,
                max_value=500,
                value=100,
                step=25,
                help="How many recent posts to collect"
            )

            comment_limit = st.slider(
                "Comments per Post",
                min_value=0,
                max_value=200,
                value=50,
                step=10,
                help="How many comments to collect per post (0 = no comments)"
            )

            submit = st.form_submit_button("Add Subreddit", use_container_width=True)

            if submit:
                if not subreddit_name:
                    st.error("Please enter a subreddit name")
                else:
                    with st.spinner("Adding subreddit..."):
                        success, result = api_client.create_reddit_subreddit(
                            subreddit_name, interval, post_limit, comment_limit
                        )

                        if success:
                            st.success(f"✅ Added subreddit: r/{subreddit_name}")
                            st.rerun()
                        else:
                            st.error(f"Failed to add subreddit: {result}")

    with col2:
        st.markdown("### Bulk Add")
        st.info("💡 Add multiple subreddits at once (one per line)")

        bulk_subreddits = st.text_area(
            "Subreddit Names",
            placeholder="python\nMachineLearning\ndatascience\nartificialintelligence",
            height=150,
            help="Enter one subreddit name per line"
        )

        bulk_interval = st.slider(
            "Monitoring Interval (bulk)",
            min_value=600,
            max_value=86400,
            value=1800,
            step=300,
            key="bulk_interval"
        )

        bulk_post_limit = st.slider(
            "Posts to Track (bulk)",
            min_value=1,
            max_value=500,
            value=100,
            step=25,
            key="bulk_post_limit"
        )

        bulk_comment_limit = st.slider(
            "Comments per Post (bulk)",
            min_value=0,
            max_value=200,
            value=50,
            step=10,
            key="bulk_comment_limit"
        )

        if st.button("Add All Subreddits", use_container_width=True):
            subreddit_names = [s.strip() for s in bulk_subreddits.split('\n') if s.strip()]

            if not subreddit_names:
                st.error("Please enter at least one subreddit name")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()

                # Use bulk endpoint
                status_text.text(f"Adding {len(subreddit_names)} subreddits...")
                success, result = api_client.create_reddit_subreddits_bulk(
                    subreddit_names, bulk_interval, bulk_post_limit, bulk_comment_limit
                )

                progress_bar.progress(1.0)

                if success:
                    st.success(f"✅ Added {result.get('created_count', 0)} subreddit(s)")
                    if result.get('failed_count', 0) > 0:
                        st.warning(f"⚠️ {result['failed_count']} subreddit(s) failed")
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

    # Load all subreddits for statistics
    success, subreddits = api_client.list_reddit_subreddits()

    if success and subreddits:
        total_subreddits = len(subreddits)
        monitoring_subreddits = sum(1 for s in subreddits if s.get("is_monitoring"))
        total_posts = sum(s.get("total_posts", 0) for s in subreddits)
        total_comments = sum(s.get("total_comments", 0) for s in subreddits)

        # Display overall metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Subreddits", total_subreddits)

        with col2:
            st.metric("Monitoring", monitoring_subreddits)

        with col3:
            st.metric("Total Posts", f"{total_posts:,}")

        with col4:
            st.metric("Total Comments", f"{total_comments:,}")

        st.markdown("---")

        # Subreddits table
        st.subheader("All Subreddits Overview")

        df_data = []
        for sub in subreddits:
            df_data.append({
                "Subreddit": f"r/{sub['subreddit_name']}",
                "Status": "🟢 Monitoring" if sub.get("is_monitoring") else "⚫ Idle",
                "Posts": sub.get("total_posts", 0),
                "Comments": sub.get("total_comments", 0),
                "Interval (s)": sub.get("monitoring_interval_seconds", 1800),
                "Post Limit": sub.get("post_limit", 100),
                "Comment Limit": sub.get("comment_limit", 50),
                "Last Collected": sub.get("last_collected", "Never")[:19] if sub.get("last_collected") else "Never"
            })

        if df_data:
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

    else:
        st.info("No subreddits to display statistics for")

st.markdown("---")
st.caption("💡 **Tip:** Background monitoring runs automatically. Posts and comments are collected even when this page is closed.")
