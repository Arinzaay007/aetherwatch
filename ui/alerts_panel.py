"""
AetherWatch — Alerts & Logs Panel
Real-time scrolling alert feed with visual severity indicators,
filterable by level, source, and time range.
"""

import datetime
import streamlit as st
import pandas as pd
from utils.alerts import get_recent_alerts, clear_alerts, AlertLevel, AlertRecord


# ── Severity styling ──────────────────────────────────────────────────────────

LEVEL_STYLES = {
    AlertLevel.CRITICAL: {"bg": "#3d0000", "border": "#f85149", "emoji": "🚨"},
    AlertLevel.ANOMALY:  {"bg": "#2d1800", "border": "#d29922", "emoji": "🔴"},
    AlertLevel.WARNING:  {"bg": "#1f2200", "border": "#d29922", "emoji": "⚠️"},
    AlertLevel.INFO:     {"bg": "#0d1f0d", "border": "#3fb950", "emoji": "ℹ️"},
}


def _alert_card_html(alert: AlertRecord) -> str:
    """Render an individual alert as a styled HTML card."""
    style = LEVEL_STYLES.get(alert.level, LEVEL_STYLES[AlertLevel.INFO])
    emoji = style["emoji"]
    ts = alert.timestamp.strftime("%H:%M:%S")
    
    return f"""
    <div style="
        background:{style['bg']};
        border-left: 3px solid {style['border']};
        border-radius: 4px;
        padding: 8px 12px;
        margin-bottom: 6px;
        font-family: monospace;
        font-size: 12px;
        color: #e6edf3;
    ">
        <span style="color:{style['border']}">{emoji} {alert.level}</span>
        <span style="color:#8b949e; margin-left:8px">{ts} UTC</span>
        <span style="color:#58a6ff; margin-left:8px">[{alert.source}]</span><br>
        <span style="color:#e6edf3; margin-top:4px; display:block">{alert.message}</span>
        {f'<span style="color:#8b949e; font-size:11px">{alert.details}</span>' if alert.details else ''}
    </div>"""


def render_alerts_panel():
    """Render the full alerts and logs panel."""
    st.subheader("🚨 Alerts & System Log")
    
    # Controls row
    ctrl1, ctrl2, ctrl3, ctrl4 = st.columns([2, 2, 2, 1])
    
    with ctrl1:
        filter_level = st.multiselect(
            "Filter by Level",
            [AlertLevel.CRITICAL, AlertLevel.ANOMALY, AlertLevel.WARNING, AlertLevel.INFO],
            default=[AlertLevel.CRITICAL, AlertLevel.ANOMALY, AlertLevel.WARNING, AlertLevel.INFO],
        )
    
    with ctrl2:
        filter_source = st.text_input("Filter by Source", placeholder="e.g., Aviation API")
    
    with ctrl3:
        max_alerts = st.slider("Max Alerts Shown", 5, 100, 30)
    
    with ctrl4:
        st.write("")
        if st.button("🗑️ Clear", type="secondary"):
            clear_alerts()
            st.rerun()
    
    # Fetch and filter alerts
    alerts = get_recent_alerts(limit=max_alerts)
    
    if filter_level:
        alerts = [a for a in alerts if a.level in filter_level]
    
    if filter_source.strip():
        src_filter = filter_source.strip().lower()
        alerts = [a for a in alerts if src_filter in a.source.lower()]
    
    # Summary stats bar
    all_alerts = get_recent_alerts(limit=200)
    critical_count = sum(1 for a in all_alerts if a.level == AlertLevel.CRITICAL)
    anomaly_count = sum(1 for a in all_alerts if a.level == AlertLevel.ANOMALY)
    warning_count = sum(1 for a in all_alerts if a.level == AlertLevel.WARNING)
    
    stat_cols = st.columns(4)
    with stat_cols[0]:
        st.metric("Total Events", len(all_alerts))
    with stat_cols[1]:
        st.metric("🚨 Critical", critical_count, delta=None if critical_count == 0 else f"+{critical_count}")
    with stat_cols[2]:
        st.metric("🔴 Anomalies", anomaly_count)
    with stat_cols[3]:
        st.metric("⚠️ Warnings", warning_count)
    
    st.markdown("---")
    
    if not alerts:
        st.info("✅ No alerts matching filters. System operating normally.")
        return
    
    # Render alert cards in a scrollable container
    alert_html = "".join(_alert_card_html(a) for a in alerts)
    st.markdown(
        f"""<div style="max-height:450px; overflow-y:auto; padding-right:4px">
            {alert_html}
        </div>""",
        unsafe_allow_html=True,
    )
    
    st.markdown("---")
    
    # Export as DataFrame
    with st.expander("📊 Export Alert Log", expanded=False):
        df = pd.DataFrame([a.to_dict() for a in get_recent_alerts(limit=200)])
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False)
            st.download_button(
                "⬇️ Download as CSV",
                data=csv,
                file_name=f"aetherwatch_alerts_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
            )
