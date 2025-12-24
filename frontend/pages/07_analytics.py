"""Analytics Dashboard Page."""

import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Analytics Dashboard", page_icon="📊", layout="wide")

# Check authentication
if "token" not in st.session_state or "user" not in st.session_state:
    st.error("⚠️ Please login first")
    st.stop()

# Initialize API client
api_client = st.session_state.api_client

st.title("📊 Analytics Dashboard")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📈 Engagement", "😊 Sentiment", "📉 Trends", "⏰ Posting Times"])

with tab1:
    st.subheader("Cross-Platform Engagement Analysis")

    col1, col2 = st.columns([1, 3])

    with col1:
        days = st.slider("Analysis Period (days)", min_value=1, max_value=90, value=7, key="engagement_days")
        selected_platforms = st.multiselect(
            "Platforms",
            options=["twitter", "youtube", "reddit", "twitch"],
            default=["twitter", "youtube", "reddit", "twitch"]
        )

        if st.button("🔄 Refresh Engagement", use_container_width=True):
            st.rerun()

    with col2:
        if selected_platforms:
            with st.spinner("Loading engagement data..."):
                platforms_str = ",".join(selected_platforms)
                success, data = api_client.get_cross_platform_engagement(days, platforms_str)

                if success and data:
                    st.info(f"📅 Data from {data['date_from'][:10]} to {data['date_to'][:10]}")

                    engagement_summary = data.get('engagement_summary', {})

                    # Display metrics in grid
                    cols = st.columns(len(selected_platforms))

                    for idx, platform in enumerate(selected_platforms):
                        with cols[idx]:
                            if platform in engagement_summary:
                                platform_data = engagement_summary[platform]

                                st.markdown(f"### {platform.title()}")

                                if platform == 'reddit':
                                    st.metric(
                                        "Avg Engagement Score",
                                        f"{platform_data.get('average_score', 0):.1f}"
                                    )
                                else:
                                    st.metric(
                                        "Avg Engagement Rate",
                                        f"{platform_data.get('average_rate', 0):.2f}%"
                                    )

                                st.metric("Total Items", platform_data.get('total_items', 0))
                                category = platform_data.get('category', 'N/A')

                                # Color-code category
                                if category == 'Excellent':
                                    st.success(f"✅ {category}")
                                elif category == 'High':
                                    st.info(f"🔵 {category}")
                                elif category == 'Medium':
                                    st.warning(f"🟡 {category}")
                                else:
                                    st.caption(f"Category: {category}")

                    st.markdown("---")

                    # Create comparison DataFrame
                    comparison_data = []
                    for platform in selected_platforms:
                        if platform in engagement_summary:
                            pdata = engagement_summary[platform]
                            comparison_data.append({
                                'Platform': platform.title(),
                                'Items': pdata.get('total_items', 0),
                                'Avg Rate/Score': pdata.get('average_rate') or pdata.get('average_score', 0),
                                'Category': pdata.get('category', 'N/A')
                            })

                    if comparison_data:
                        df = pd.DataFrame(comparison_data)
                        st.dataframe(df, use_container_width=True, hide_index=True)

                else:
                    st.warning("No engagement data available")
        else:
            st.info("Please select at least one platform")

with tab2:
    st.subheader("Sentiment Analysis")

    col1, col2 = st.columns([1, 3])

    with col1:
        sentiment_platform = st.selectbox(
            "Select Platform",
            options=["twitter", "reddit", "youtube"],
            key="sentiment_platform"
        )

        sentiment_days = st.slider(
            "Analysis Period (days)",
            min_value=1,
            max_value=90,
            value=7,
            key="sentiment_days"
        )

        sentiment_limit = st.slider(
            "Max Items to Analyze",
            min_value=10,
            max_value=500,
            value=100,
            step=10,
            key="sentiment_limit"
        )

        if st.button("🔍 Analyze Sentiment", use_container_width=True):
            st.session_state['run_sentiment'] = True

    with col2:
        if st.session_state.get('run_sentiment', False):
            with st.spinner(f"Analyzing {sentiment_platform} content..."):
                success, data = api_client.get_platform_sentiment(
                    sentiment_platform, sentiment_days, sentiment_limit
                )

                if success and data:
                    st.success(f"✅ Analyzed {data['total_items']} items")

                    # Sentiment distribution
                    dist = data.get('sentiment_distribution', {})
                    col_a, col_b, col_c, col_d = st.columns(4)

                    with col_a:
                        st.metric("Positive", dist.get('positive', 0), delta_color="normal")
                    with col_b:
                        st.metric("Neutral", dist.get('neutral', 0))
                    with col_c:
                        st.metric("Negative", dist.get('negative', 0), delta_color="inverse")
                    with col_d:
                        avg_compound = data.get('average_compound', 0)
                        st.metric("Avg Compound", f"{avg_compound:.3f}")

                    st.markdown("---")

                    # Show recent items with sentiment
                    items = data.get('items', [])
                    if items:
                        st.markdown("### Recent Content with Sentiment")

                        for item in items[:10]:  # Show top 10
                            sentiment = item.get('sentiment', {})
                            label = sentiment.get('label', 'Neutral')

                            if label == 'Positive':
                                emoji = "😊"
                                color = "green"
                            elif label == 'Negative':
                                emoji = "😞"
                                color = "red"
                            else:
                                emoji = "😐"
                                color = "gray"

                            with st.container():
                                st.markdown(f"**{emoji} {label}** (Compound: {sentiment.get('compound', 0):.3f})")
                                st.caption(f"Created: {item.get('created_at', 'Unknown')[:19]} | Engagement: {item.get('engagement', 0)}")
                                st.markdown("---")

                    st.session_state['run_sentiment'] = False

                else:
                    st.error("Failed to analyze sentiment")
        else:
            st.info("Click 'Analyze Sentiment' to start analysis")

with tab3:
    st.subheader("Trend Analysis")

    col1, col2 = st.columns([1, 3])

    with col1:
        trend_platform = st.selectbox(
            "Select Platform",
            options=["twitter", "youtube", "reddit"],
            key="trend_platform"
        )

        trend_metric = st.selectbox(
            "Metric",
            options=["engagement", "likes", "views", "upvotes"],
            key="trend_metric"
        )

        trend_days = st.slider(
            "Analysis Period (days)",
            min_value=7,
            max_value=90,
            value=30,
            key="trend_days"
        )

        if st.button("📊 Analyze Trends", use_container_width=True):
            st.session_state['run_trends'] = True

    with col2:
        if st.session_state.get('run_trends', False):
            with st.spinner("Analyzing trends..."):
                success, data = api_client.get_platform_trends(
                    trend_platform, trend_metric, trend_days
                )

                if success and data:
                    trend_analysis = data.get('trend_analysis', {})

                    # Metrics
                    col_a, col_b, col_c, col_d = st.columns(4)

                    with col_a:
                        direction = trend_analysis.get('trend_direction', 'stable')
                        if direction == 'upward':
                            st.success(f"📈 {direction.title()}")
                        elif direction == 'downward':
                            st.error(f"📉 {direction.title()}")
                        else:
                            st.info(f"➡️ {direction.title()}")

                    with col_b:
                        st.metric("Average", f"{trend_analysis.get('average_value', 0):.1f}")
                    with col_c:
                        st.metric("Peak", trend_analysis.get('peak_value', 0))
                    with col_d:
                        st.metric("Volatility", f"{trend_analysis.get('volatility', 0):.1f}")

                    st.markdown("---")

                    # Forecast
                    forecast = data.get('forecast', {})
                    if forecast:
                        st.markdown("### 📮 Forecast")
                        fcol1, fcol2, fcol3 = st.columns(3)

                        with fcol1:
                            st.metric("Next Period Forecast", f"{forecast.get('forecast', 0):.1f}")
                        with fcol2:
                            confidence = forecast.get('confidence', 'low')
                            st.caption(f"Confidence: {confidence.upper()}")
                        with fcol3:
                            st.caption(f"Method: {forecast.get('method', 'N/A')}")

                    # Anomalies
                    anomalies = data.get('anomalies', [])
                    if anomalies:
                        st.markdown("### ⚠️ Anomalies Detected")
                        st.caption(f"Found {len(anomalies)} anomalies (values >2 std deviations from mean)")

                        for anomaly in anomalies[:5]:
                            st.warning(
                                f"**{anomaly.get('timestamp', 'Unknown')[:19]}**: "
                                f"Value: {anomaly.get('value', 0)} | "
                                f"Z-Score: {anomaly.get('z_score', 0):.2f}"
                            )

                    st.session_state['run_trends'] = False

                else:
                    st.error("Failed to analyze trends")
        else:
            st.info("Click 'Analyze Trends' to start analysis")

with tab4:
    st.subheader("Best Posting Times")

    col1, col2 = st.columns([1, 3])

    with col1:
        posting_platform = st.selectbox(
            "Select Platform",
            options=["twitter", "youtube", "reddit"],
            key="posting_platform"
        )

        posting_days = st.slider(
            "Analysis Period (days)",
            min_value=7,
            max_value=90,
            value=30,
            key="posting_days"
        )

        if st.button("⏰ Analyze Posting Times", use_container_width=True):
            st.session_state['run_posting'] = True

    with col2:
        if st.session_state.get('run_posting', False):
            with st.spinner("Analyzing posting patterns..."):
                success, data = api_client.get_best_posting_times(posting_platform, posting_days)

                if success and data:
                    st.success(f"✅ Analyzed {data.get('total_posts_analyzed', 0)} posts")

                    best_hour = data.get('best_hour')
                    best_day = data.get('best_day')

                    if best_hour is not None and best_day:
                        col_a, col_b = st.columns(2)

                        with col_a:
                            st.metric("Best Hour (UTC)", f"{best_hour}:00")
                        with col_b:
                            st.metric("Best Day", best_day)

                        st.markdown("---")

                    # Hourly averages
                    hourly_avg = data.get('hourly_avg', {})
                    if hourly_avg:
                        st.markdown("### 📊 Hourly Engagement Patterns")

                        hourly_data = []
                        for hour, avg in sorted(hourly_avg.items()):
                            hourly_data.append({
                                'Hour (UTC)': f"{hour}:00",
                                'Avg Engagement': round(avg, 2)
                            })

                        if hourly_data:
                            df_hourly = pd.DataFrame(hourly_data)
                            st.dataframe(df_hourly, use_container_width=True, hide_index=True)

                    st.markdown("---")

                    # Daily averages
                    daily_avg = data.get('daily_avg', {})
                    if daily_avg:
                        st.markdown("### 📅 Daily Engagement Patterns")

                        days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                        daily_data = []

                        for day in days_order:
                            if day in daily_avg:
                                daily_data.append({
                                    'Day': day,
                                    'Avg Engagement': round(daily_avg[day], 2)
                                })

                        if daily_data:
                            df_daily = pd.DataFrame(daily_data)
                            st.dataframe(df_daily, use_container_width=True, hide_index=True)

                    st.session_state['run_posting'] = False

                else:
                    st.error("Failed to analyze posting times")
        else:
            st.info("Click 'Analyze Posting Times' to start analysis")

st.markdown("---")
st.caption("💡 **Tip:** Analytics are based on collected data. Ensure monitoring is active to gather sufficient data for analysis.")
