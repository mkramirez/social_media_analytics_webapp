"""Real-time Updates Page (WebSocket Monitor)."""

import streamlit as st
import json
from datetime import datetime

st.set_page_config(page_title="Real-time Updates", page_icon="⚡", layout="wide")

# Check authentication
if "token" not in st.session_state or "user" not in st.session_state:
    st.error("⚠️ Please login first")
    st.stop()

st.title("⚡ Real-time Updates")

st.info("""
**Real-time WebSocket Support**: This application supports real-time updates via WebSocket connections.

When monitoring is active, you'll receive instant notifications about:
- 📊 New data collected from platforms
- 🔔 Monitoring status changes
- 📈 Analytics updates
- ⚠️ System notifications

**Note:** WebSocket integration is implemented in the backend. A full JavaScript/React frontend would
provide seamless real-time updates without page refreshes.
""")

# Initialize API client
api_client = st.session_state.api_client

# Get WebSocket status
col1, col2 = st.columns(2)

with col1:
    st.subheader("📡 WebSocket Information")

    st.markdown("""
    ### Connection Details
    - **WebSocket URL:** `ws://localhost:8000/api/ws?token=<your_jwt_token>`
    - **Protocol:** WebSocket (WS)
    - **Authentication:** JWT token via query parameter
    - **Message Format:** JSON

    ### Supported Message Types
    1. **platform_update** - New data from platforms
    2. **monitoring_update** - Entity monitoring status changes
    3. **analytics_update** - Analytics computation results
    4. **notification** - System notifications
    5. **connection_established** - Initial connection confirmation
    """)

with col2:
    st.subheader("💬 Test Notifications")

    st.markdown("Send a test notification to your WebSocket connections:")

    test_message = st.text_area(
        "Test Message",
        value="Hello from Streamlit!",
        height=100
    )

    if st.button("📤 Send Test Notification", use_container_width=True, type="primary"):
        # Note: This would need the API client to have a method for this
        try:
            import requests
            response = requests.post(
                f"{api_client.base_url}/api/ws/broadcast/test",
                params={"message": test_message},
                headers=api_client._get_headers()
            )

            if response.status_code == 200:
                data = response.json()
                st.success(f"✅ Notification sent to {data.get('recipients', 0)} connection(s)")
            else:
                st.error(f"❌ Failed to send: {response.json().get('detail', 'Unknown error')}")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

st.markdown("---")

# WebSocket status
st.subheader("📊 Connection Status")

if st.button("🔄 Refresh Status"):
    st.rerun()

try:
    import requests
    response = requests.get(
        f"{api_client.base_url}/api/ws/status",
        headers=api_client._get_headers()
    )

    if response.status_code == 200:
        status_data = response.json()

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Total Connections",
                status_data.get("total_connections", 0)
            )

        with col2:
            st.metric(
                "Your Connections",
                status_data.get("user_connections", 0)
            )

        with col3:
            is_connected = status_data.get("is_connected", False)
            st.metric(
                "Status",
                "🟢 Connected" if is_connected else "⚫ Disconnected"
            )

        with col4:
            st.metric(
                "Active Users",
                status_data.get("active_users_count", 0)
            )

    else:
        st.error("Failed to get WebSocket status")

except Exception as e:
    st.error(f"Error getting status: {str(e)}")

st.markdown("---")

# Example WebSocket client code
st.subheader("💻 Integration Example")

st.markdown("### Python WebSocket Client Example")

python_code = f"""
import websockets
import asyncio
import json

async def connect_websocket():
    token = "{st.session_state.get('token', 'YOUR_JWT_TOKEN')}"
    uri = f"ws://localhost:8000/api/ws?token={{token}}"

    async with websockets.connect(uri) as websocket:
        print("✅ Connected to WebSocket")

        # Send ping
        await websocket.send(json.dumps({{"type": "ping"}}))

        # Listen for messages
        while True:
            message = await websocket.recv()
            data = json.loads(message)

            print(f"Received: {{data.get('type')}}")

            if data.get('type') == 'platform_update':
                print(f"  Platform: {{data.get('platform')}}")
                print(f"  Data: {{data.get('data')}}")

            elif data.get('type') == 'notification':
                notification = data.get('notification', {{}})
                print(f"  Title: {{notification.get('title')}}")
                print(f"  Message: {{notification.get('message')}}")

# Run the client
asyncio.run(connect_websocket())
"""

st.code(python_code, language="python")

st.markdown("### JavaScript WebSocket Client Example")

js_code = f"""
const token = "{st.session_state.get('token', 'YOUR_JWT_TOKEN')}";
const ws = new WebSocket(`ws://localhost:8000/api/ws?token=${{token}}`);

ws.onopen = () => {{
    console.log('✅ WebSocket connected');

    // Send ping
    ws.send(JSON.stringify({{ type: 'ping' }}));
}};

ws.onmessage = (event) => {{
    const data = JSON.parse(event.data);
    console.log('Received:', data.type);

    switch(data.type) {{
        case 'platform_update':
            console.log('Platform:', data.platform);
            console.log('Data:', data.data);
            // Update UI with new data
            break;

        case 'notification':
            const notification = data.notification;
            console.log('Notification:', notification.title);
            // Show notification to user
            break;

        case 'monitoring_update':
            console.log('Entity:', data.entity_type);
            console.log('Status:', data.status);
            // Update monitoring status in UI
            break;
    }}
}};

ws.onerror = (error) => {{
    console.error('WebSocket error:', error);
}};

ws.onclose = () => {{
    console.log('WebSocket disconnected');
    // Implement reconnection logic
}};
"""

st.code(js_code, language="javascript")

st.markdown("---")

# Performance benefits
st.subheader("🚀 Performance Benefits")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    ### Traditional Polling
    - Client requests data every N seconds
    - High server load
    - Delayed updates (polling interval)
    - Wasted bandwidth on "no changes"
    - Scales poorly with users

    **Example:** 100 users polling every 10s = 600 requests/min
    """)

with col2:
    st.markdown("""
    ### WebSocket Real-time
    - Server pushes updates instantly
    - Low server load
    - Immediate updates (< 100ms latency)
    - Only sends when data changes
    - Excellent scalability

    **Example:** 100 users connected = 100 idle connections
    """)

st.markdown("---")

# Message format reference
with st.expander("📋 Message Format Reference"):
    st.markdown("""
    ### Connection Established
    ```json
    {
        "type": "connection_established",
        "message": "WebSocket connected successfully",
        "user_id": "uuid"
    }
    ```

    ### Platform Update
    ```json
    {
        "type": "platform_update",
        "platform": "twitter",
        "timestamp": "2025-01-15T10:30:00",
        "data": {
            "entity_id": "uuid",
            "entity_name": "username",
            "new_items": 5,
            "summary": "Collected 5 new tweets"
        }
    }
    ```

    ### Monitoring Update
    ```json
    {
        "type": "monitoring_update",
        "entity_type": "twitter_user",
        "entity_id": "uuid",
        "timestamp": "2025-01-15T10:30:00",
        "status": {
            "is_monitoring": true,
            "last_collected": "2025-01-15T10:29:55",
            "items_collected": 150
        }
    }
    ```

    ### Notification
    ```json
    {
        "type": "notification",
        "timestamp": "2025-01-15T10:30:00",
        "notification": {
            "title": "Collection Complete",
            "message": "Successfully collected data from all platforms",
            "level": "success"
        }
    }
    ```

    ### Analytics Update
    ```json
    {
        "type": "analytics_update",
        "analytics_type": "engagement",
        "timestamp": "2025-01-15T10:30:00",
        "data": {
            "platform": "twitter",
            "average_engagement": 3.5,
            "total_items": 100
        }
    }
    ```
    """)

st.caption("💡 **Tip:** In a production React/Vue/Angular frontend, WebSocket updates would seamlessly update the UI without page refreshes.")
