import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# ================= CONFIG =================
BACKEND_URL = "http://127.0.0.1:8001"

st.set_page_config(
    page_title="System Anomaly Monitoring",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ================= STYLES =================
st.markdown("""
<style>
.stApp {
    background-color: #0b0f1a;
    color: #e5e7eb;
}
.card {
    background: #111827;
    padding: 20px;
    border-radius: 16px;
    box-shadow: 0 0 20px rgba(0,0,0,0.4);
}
.metric-title {
    font-size: 13px;
    color: #9ca3af;
}
.metric-value {
    font-size: 34px;
    font-weight: 700;
}
.alert-critical {
    background: #3b0a0a;
    border-left: 6px solid #ef4444;
    padding: 15px;
    border-radius: 10px;
    margin-bottom: 12px;
}
</style>
""", unsafe_allow_html=True)

# ================= SIDEBAR =================
st.sidebar.title("⚙️ Controls")

# ================= FETCH DATA =================
metrics = requests.get(f"{BACKEND_URL}/metrics").json()
status = requests.get(f"{BACKEND_URL}/status").json()
alerts = requests.get(f"{BACKEND_URL}/alerts").json()

df = pd.DataFrame(metrics)

node = st.sidebar.selectbox(
    "Select Node",
    df["node_id"].unique()
)

node_df = df[df["node_id"] == node]
latest = node_df.iloc[-1]

# ================= HEADER =================
st.markdown("## 🖥️ System Anomaly Monitoring Dashboard")
st.markdown(
    "Real‑time CPU, Memory & Disk monitoring with **ML‑based anomaly detection**"
)

# ================= STATUS + METRICS =================
col1, col2, col3, col4 = st.columns(4)

def status_icon(s):
    if s == "Normal":
        return "🟢"
    if s == "Warning":
        return "🟠"
    return "🔴"

with col1:
    st.markdown(f"""
    <div class="card">
        <div class="metric-title">SYSTEM STATUS</div>
        <div class="metric-value">
            {status_icon(status["status"])} {status["status"]}
        </div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="card">
        <div class="metric-title">CPU USAGE</div>
        <div class="metric-value">{latest.cpu}%</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="card">
        <div class="metric-title">MEMORY USAGE</div>
        <div class="metric-value">{latest.memory}%</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="card">
        <div class="metric-title">DISK USAGE</div>
        <div class="metric-value">{latest.disk}%</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ================= CHARTS =================
def chart(metric, color):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[datetime.fromtimestamp(t) for t in node_df["timestamp"]],
        y=node_df[metric],
        line=dict(color=color, width=3),
        fill="tozeroy",
    ))
    fig.update_layout(
        height=280,
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font=dict(color="#e5e7eb"),
        margin=dict(l=20, r=20, t=30, b=20),
        showlegend=False
    )
    return fig

c1, c2, c3 = st.columns(3)
with c1:
    st.plotly_chart(chart("cpu", "#22d3ee"), use_container_width=True)
with c2:
    st.plotly_chart(chart("memory", "#facc15"), use_container_width=True)
with c3:
    st.plotly_chart(chart("disk", "#f87171"), use_container_width=True)

# ================= ALERT HISTORY =================
st.markdown("## 🚨 Critical Alerts")

if alerts:
    for alert in reversed(alerts[-5:]):
        time_str = datetime.fromtimestamp(
            alert["timestamp"]
        ).strftime("%Y-%m-%d %H:%M:%S")

        clean_message = alert["message"].replace("\n", "<br>")

        st.markdown(f"""
        <div class="alert-critical">
            <div style="font-size:14px; font-weight:600; color:#fecaca;">
                🚨 {alert["level"]}
            </div>
            <div style="font-size:12px; color:#9ca3af; margin-bottom:6px;">
                {time_str}
            </div>
            <div style="font-size:14px; line-height:1.5;">
                {clean_message}
            </div>
        </div>
        """, unsafe_allow_html=True)

    last_time = datetime.fromtimestamp(
        alerts[-1]["timestamp"]
    ).strftime("%Y-%m-%d %H:%M:%S")

    st.success(f"📧 Last alert email sent at {last_time}")
else:
    st.info("No critical alerts detected yet")
