"""
Feedback Page

Allows users to submit feedback, bug reports, and feature requests.
"""

import streamlit as st
from components.api_client import APIClient
from datetime import datetime


def show_feedback_page():
    """Display feedback page."""
    st.title("📢 Feedback & Support")

    st.write("""
    We value your feedback! Help us improve by reporting bugs, suggesting features,
    or sharing your thoughts about the platform.
    """)

    # Check authentication
    if "access_token" not in st.session_state:
        st.warning("Please log in to submit feedback")
        return

    api = APIClient(st.session_state["access_token"])

    # Tabs for different sections
    tab1, tab2, tab3 = st.tabs(["📝 Submit Feedback", "📋 My Feedback", "📊 Statistics"])

    with tab1:
        show_submit_feedback_form(api)

    with tab2:
        show_my_feedback(api)

    with tab3:
        show_feedback_stats(api)


def show_submit_feedback_form(api: APIClient):
    """Show feedback submission form."""
    st.subheader("Submit New Feedback")

    with st.form("feedback_form"):
        # Feedback type
        feedback_type = st.selectbox(
            "Type",
            options=["bug", "feature_request", "improvement", "question", "other"],
            format_func=lambda x: {
                "bug": "🐛 Bug Report",
                "feature_request": "💡 Feature Request",
                "improvement": "⚡ Improvement Suggestion",
                "question": "❓ Question",
                "other": "📌 Other"
            }[x]
        )

        # Title
        title = st.text_input(
            "Title",
            placeholder="Brief summary of your feedback",
            max_chars=200
        )

        # Description
        description = st.text_area(
            "Description",
            placeholder="Please provide detailed information...",
            height=200,
            max_chars=5000
        )

        # Ratings (optional)
        col1, col2 = st.columns(2)

        with col1:
            satisfaction_rating = st.select_slider(
                "Overall Satisfaction (Optional)",
                options=[1, 2, 3, 4, 5],
                value=3,
                format_func=lambda x: "⭐" * x
            )
            use_satisfaction = st.checkbox("Include satisfaction rating", value=False)

        with col2:
            feature_rating = st.select_slider(
                "Feature Rating (Optional)",
                options=[1, 2, 3, 4, 5],
                value=3,
                format_func=lambda x: "⭐" * x
            )
            use_feature = st.checkbox("Include feature rating", value=False)

        # Current page URL (auto-filled)
        page_url = st.text_input(
            "Page URL (Optional)",
            value=st.session_state.get("current_page", ""),
            disabled=True
        )

        # Submit button
        submitted = st.form_submit_button("Submit Feedback", use_container_width=True)

        if submitted:
            # Validation
            if not title or len(title) < 5:
                st.error("Title must be at least 5 characters")
                return

            if not description or len(description) < 10:
                st.error("Description must be at least 10 characters")
                return

            # Prepare payload
            payload = {
                "type": feedback_type,
                "title": title,
                "description": description,
                "page_url": page_url if page_url else None
            }

            if use_satisfaction:
                payload["satisfaction_rating"] = satisfaction_rating

            if use_feature:
                payload["feature_rating"] = feature_rating

            # Submit
            try:
                result = api.post("/api/feedback", json=payload)

                if result:
                    st.success("✅ Thank you! Your feedback has been submitted.")
                    st.balloons()

                    # Show confirmation
                    st.info(f"Feedback ID: {result.get('id')}")

                    # Clear form (rerun)
                    st.rerun()
                else:
                    st.error("Failed to submit feedback")

            except Exception as e:
                st.error(f"Error submitting feedback: {str(e)}")


def show_my_feedback(api: APIClient):
    """Show user's submitted feedback."""
    st.subheader("My Feedback")

    # Filters
    col1, col2 = st.columns(2)

    with col1:
        filter_type = st.selectbox(
            "Filter by Type",
            options=["all", "bug", "feature_request", "improvement", "question", "other"],
            format_func=lambda x: "All Types" if x == "all" else x.replace("_", " ").title()
        )

    with col2:
        filter_status = st.selectbox(
            "Filter by Status",
            options=["all", "new", "reviewing", "planned", "in_progress", "completed", "wont_fix"],
            format_func=lambda x: "All Status" if x == "all" else x.replace("_", " ").title()
        )

    # Fetch feedback
    try:
        params = {}
        if filter_type != "all":
            params["type"] = filter_type
        if filter_status != "all":
            params["status"] = filter_status

        feedback_list = api.get("/api/feedback", params=params)

        if not feedback_list:
            st.info("No feedback submitted yet")
            return

        st.write(f"Found {len(feedback_list)} feedback items")

        # Display feedback
        for feedback in feedback_list:
            with st.expander(
                f"[{feedback['type'].upper()}] {feedback['title']} - {feedback['status'].replace('_', ' ').title()}",
                expanded=False
            ):
                st.write(f"**ID:** {feedback['id']}")
                st.write(f"**Status:** {feedback['status'].replace('_', ' ').title()}")
                st.write(f"**Type:** {feedback['type'].replace('_', ' ').title()}")
                st.write(f"**Submitted:** {datetime.fromisoformat(feedback['created_at']).strftime('%Y-%m-%d %H:%M')}")

                st.markdown("---")
                st.write("**Description:**")
                st.write(feedback['description'])

                if feedback.get('satisfaction_rating'):
                    st.write(f"**Satisfaction:** {'⭐' * feedback['satisfaction_rating']}")

                if feedback.get('feature_rating'):
                    st.write(f"**Feature Rating:** {'⭐' * feedback['feature_rating']}")

                # Delete button
                if st.button(f"Delete Feedback #{feedback['id']}", key=f"delete_{feedback['id']}"):
                    if st.session_state.get(f"confirm_delete_{feedback['id']}", False):
                        try:
                            api.delete(f"/api/feedback/{feedback['id']}")
                            st.success("Feedback deleted")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error deleting feedback: {e}")
                    else:
                        st.session_state[f"confirm_delete_{feedback['id']}"] = True
                        st.warning("Click again to confirm deletion")

    except Exception as e:
        st.error(f"Error loading feedback: {str(e)}")


def show_feedback_stats(api: APIClient):
    """Show feedback statistics."""
    st.subheader("Feedback Statistics")

    try:
        stats = api.get("/api/feedback/stats/summary")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total Feedback", stats.get("total", 0))

        with col2:
            completed = stats.get("by_status", {}).get("completed", 0)
            st.metric("Completed", completed)

        with col3:
            in_progress = stats.get("by_status", {}).get("in_progress", 0)
            st.metric("In Progress", in_progress)

        # By type breakdown
        st.markdown("### By Type")
        by_type = stats.get("by_type", {})

        type_data = {
            "Bug Reports": by_type.get("bug", 0),
            "Feature Requests": by_type.get("feature_request", 0),
            "Improvements": by_type.get("improvement", 0),
            "Questions": by_type.get("question", 0),
            "Other": by_type.get("other", 0)
        }

        for label, count in type_data.items():
            st.write(f"**{label}:** {count}")

        # By status breakdown
        st.markdown("### By Status")
        by_status = stats.get("by_status", {})

        status_data = {
            "New": by_status.get("new", 0),
            "Reviewing": by_status.get("reviewing", 0),
            "Planned": by_status.get("planned", 0),
            "In Progress": by_status.get("in_progress", 0),
            "Completed": by_status.get("completed", 0),
            "Won't Fix": by_status.get("wont_fix", 0)
        }

        for label, count in status_data.items():
            st.write(f"**{label}:** {count}")

    except Exception as e:
        st.error(f"Error loading statistics: {str(e)}")


if __name__ == "__main__":
    show_feedback_page()
