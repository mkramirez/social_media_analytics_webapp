"""Data Export Page."""

import streamlit as st
from datetime import datetime
import base64

st.set_page_config(page_title="Data Export", page_icon="📥", layout="wide")

# Check authentication
if "token" not in st.session_state or "user" not in st.session_state:
    st.error("⚠️ Please login first")
    st.stop()

# Initialize API client
api_client = st.session_state.api_client

st.title("📥 Data Export")

# Get export summary
with st.spinner("Loading export summary..."):
    success, summary = api_client.get_export_summary()

if success and summary:
    st.info("Export your collected social media data to CSV format for analysis in other tools.")

    # Display summary
    st.subheader("📊 Available Data")

    available = summary.get('available_data', {})
    total_records = summary.get('total_records', 0)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        twitter_data = available.get('twitter', {})
        st.metric("Twitter Tweets", f"{twitter_data.get('count', 0):,}")
        if twitter_data.get('earliest_date'):
            st.caption(f"Since: {twitter_data['earliest_date'][:10]}")

    with col2:
        youtube_data = available.get('youtube', {})
        st.metric("YouTube Videos", f"{youtube_data.get('count', 0):,}")
        if youtube_data.get('earliest_date'):
            st.caption(f"Since: {youtube_data['earliest_date'][:10]}")

    with col3:
        reddit_data = available.get('reddit', {})
        st.metric("Reddit Posts", f"{reddit_data.get('count', 0):,}")
        if reddit_data.get('earliest_date'):
            st.caption(f"Since: {reddit_data['earliest_date'][:10]}")

    with col4:
        twitch_data = available.get('twitch', {})
        st.metric("Twitch Streams", f"{twitch_data.get('count', 0):,}")
        if twitch_data.get('earliest_date'):
            st.caption(f"Since: {twitch_data['earliest_date'][:10]}")

    st.markdown("---")

    # Export options
    st.subheader("📤 Export Options")

    tab1, tab2 = st.tabs(["Single Platform", "All Platforms"])

    with tab1:
        st.markdown("### Export Single Platform Data")

        col1, col2 = st.columns(2)

        with col1:
            platform = st.selectbox(
                "Select Platform",
                options=["twitter", "youtube", "reddit", "twitch"],
                format_func=lambda x: x.title()
            )

            days = st.slider(
                "Export data from last N days",
                min_value=1,
                max_value=365,
                value=30,
                help="Select how many days of historical data to export"
            )

            # Show estimated record count
            platform_count = available.get(platform, {}).get('count', 0)
            st.info(f"📊 This platform has **{platform_count:,}** total records")

        with col2:
            st.markdown("**Export Details:**")
            st.markdown(f"""
            - **Platform:** {platform.title()}
            - **Period:** Last {days} days
            - **Format:** CSV
            - **Content:** All collected data with metrics
            """)

            export_button = st.button(
                f"📥 Export {platform.title()} Data",
                use_container_width=True,
                type="primary"
            )

            if export_button:
                with st.spinner(f"Generating {platform} export..."):
                    success, csv_data = api_client.export_csv(platform, days)

                    if success and csv_data:
                        # Create download button
                        filename = f"{platform}_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

                        st.download_button(
                            label=f"⬇️ Download {filename}",
                            data=csv_data,
                            file_name=filename,
                            mime="text/csv",
                            use_container_width=True
                        )

                        st.success(f"✅ Export ready! Click the button above to download.")
                    else:
                        st.error(f"❌ Failed to export {platform} data. {csv_data if csv_data else 'No data available.'}")

    with tab2:
        st.markdown("### Export All Platforms Combined")

        col1, col2 = st.columns(2)

        with col1:
            all_days = st.slider(
                "Export data from last N days (all platforms)",
                min_value=1,
                max_value=365,
                value=30,
                key="all_days",
                help="Select how many days of historical data to export from all platforms"
            )

            st.info(f"📊 Total records across all platforms: **{total_records:,}**")

        with col2:
            st.markdown("**Export Details:**")
            st.markdown(f"""
            - **Platforms:** Twitter, YouTube, Reddit, Twitch
            - **Period:** Last {all_days} days
            - **Format:** CSV (combined)
            - **Content:** All data with platform identifiers
            """)

            export_all_button = st.button(
                "📥 Export All Platforms",
                use_container_width=True,
                type="primary",
                key="export_all"
            )

            if export_all_button:
                with st.spinner("Generating combined export..."):
                    success, csv_data = api_client.export_csv("all", all_days)

                    if success and csv_data:
                        filename = f"all_platforms_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

                        st.download_button(
                            label=f"⬇️ Download {filename}",
                            data=csv_data,
                            file_name=filename,
                            mime="text/csv",
                            use_container_width=True
                        )

                        st.success("✅ Combined export ready! Click the button above to download.")
                    else:
                        st.error(f"❌ Failed to export data. {csv_data if csv_data else 'No data available.'}")

    st.markdown("---")

    # Export information
    st.subheader("ℹ️ Export Information")

    info_col1, info_col2 = st.columns(2)

    with info_col1:
        st.markdown("""
        ### Supported Formats
        - **CSV** - Comma-separated values (Excel compatible)

        ### What's Included
        Each platform export contains:
        - **Twitter:** Tweet text, metrics (likes, retweets, replies), timestamps
        - **YouTube:** Video titles, descriptions, views, likes, comments
        - **Reddit:** Post titles, text, upvotes, comments, subreddit
        - **Twitch:** Stream info, viewer counts, chat metrics
        """)

    with info_col2:
        st.markdown("""
        ### Usage Tips
        - Export recent data (7-30 days) for faster downloads
        - Large exports may take longer to generate
        - CSV files can be opened in Excel, Google Sheets, or data analysis tools
        - Use single platform exports for focused analysis
        - Use combined export for cross-platform comparison

        ### Data Privacy
        - Exports contain only YOUR monitored data
        - No personal credentials are included
        - Downloads are temporary and not stored on server
        """)

else:
    st.error("Failed to load export summary. Please try again.")

st.markdown("---")
st.caption("💡 **Tip:** Exported data is generated in real-time from your database. Regular exports can serve as backups of your collected data.")
