import streamlit as st
import pandas as pd
import altair as alt
import os
from src import config

# ---------------------------------------------------
# Page Config
# ---------------------------------------------------
st.set_page_config(
    page_title="NYC Congestion Pricing Audit",
    layout="wide"
)

# Reduce excessive padding
st.markdown("""
    <style>
    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

st.title("NYC Congestion Pricing Audit — 2025")
st.markdown("### Auditing the impact of the Manhattan Relief Zone Toll")

# ---------------------------------------------------
# Data Loader
# ---------------------------------------------------
@st.cache_data
def load_data(filename):
    path = config.OUTPUT_DIR / filename
    if not path.exists():
        return None
    try:
        if filename.endswith(".parquet"):
            return pd.read_parquet(path)
        elif filename.endswith(".csv"):
            return pd.read_csv(path)
    except Exception as e:
        st.error(f"Error loading {filename}: {e}")
        return None


# ---------------------------------------------------
# Tabs
# ---------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "Map: Border Effect",
    "Flow: Heatmaps",
    "Economics: Tips",
    "Weather: Elasticity"
])

# ===================================================
# TAB 1 — BORDER EFFECT
# ===================================================
with tab1:
    st.header("Border Effect Analysis")
    st.write("Hypothesis: Riders drop off just outside the toll zone to avoid the surcharge.")

    border_data = load_data("border_stats.parquet")

    if border_data is not None and not border_data.empty:

        chart = (
            alt.Chart(border_data)
            .mark_bar()
            .encode(
                x=alt.X("dropoff_loc:N", title="Dropoff Location"),
                y=alt.Y("dropoff_count:Q", title="Dropoff Count"),
                color=alt.Color("year:N", legend=alt.Legend(title="Year")),
                column=alt.Column("year:N", title=None)
            )
            .properties(height=450)
        )

        st.altair_chart(chart, use_container_width=True)

    else:
        st.warning("Border data not available. Run the pipeline first.")


# ===================================================
# TAB 2 — HEATMAP
# ===================================================
with tab2:
    st.header("Congestion Velocity Heatmap")
    st.write("Hypothesis: The toll improves traffic speed inside the zone.")

    velocity_data = load_data("velocity_heatmap.parquet")

    if velocity_data is not None and not velocity_data.empty:

        heatmap = (
            alt.Chart(velocity_data)
            .mark_rect()
            .encode(
                x=alt.X("hour:O", title="Hour of Day"),
                y=alt.Y("dow:O", title="Day of Week"),
                color=alt.Color(
                    "avg_speed:Q",
                    scale=alt.Scale(scheme="viridis"),
                    title="Avg Speed"
                ),
                tooltip=["hour", "dow", "avg_speed"]
            )
            .properties(height=500)
        )

        st.altair_chart(heatmap, use_container_width=True)

    else:
        st.warning("Velocity heatmap data not available.")


# ===================================================
# TAB 3 — ECONOMICS
# ===================================================
with tab3:
    st.header("Tip Crowding-Out & Leakage")

    col1, col2 = st.columns(2)

    # ---------- TIP VS SURCHARGE ----------
    with col1:
        st.subheader("Tip vs Surcharge")

        tip_data = load_data("tip_stats.parquet")

        if tip_data is not None and not tip_data.empty:

            base = alt.Chart(tip_data).encode(
                x=alt.X("month:O", title="Month")
            )

            line1 = base.mark_line(
                color="blue",
                strokeWidth=3
            ).encode(
                y=alt.Y(
                    "avg_surcharge:Q",
                    axis=alt.Axis(title="Avg Surcharge ($)", titleColor="blue")
                )
            )

            line2 = base.mark_line(
                color="green",
                strokeWidth=3
            ).encode(
                y=alt.Y(
                    "tip_pct:Q",
                    axis=alt.Axis(title="Tip %", titleColor="green")
                )
            )

            dual_chart = alt.layer(line1, line2).resolve_scale(
                y="independent"
            ).properties(height=450)

            st.altair_chart(dual_chart, use_container_width=True)

        else:
            st.warning("Tip statistics data not available.")

    # ---------- LEAKAGE TABLE ----------
    with col2:
        st.subheader("Top Missing Surcharge Locations")

        leakage_data = load_data("top_missing_surcharge_locs.parquet")

        if leakage_data is not None and not leakage_data.empty:
            st.dataframe(
                leakage_data,
                use_container_width=True,
                height=450
            )
        else:
            st.warning("Leakage audit data not available.")


# ===================================================
# TAB 4 — WEATHER
# ===================================================
with tab4:
    st.header("Rain Elasticity Analysis")
    st.write("Hypothesis: Demand is inelastic during rain, supporting dynamic pricing.")

    elasticity_file = config.OUTPUT_DIR / "rain_elasticity.txt"

    if elasticity_file.exists():
        with open(elasticity_file, "r") as f:
            score = f.read().strip()

        st.metric("Rain Elasticity Score", score)

    else:
        st.warning("Elasticity score not available.")

    st.info("Elasticity computed using Pearson correlation of daily trips vs precipitation.")


# ===================================================
# SIDEBAR
# ===================================================
st.sidebar.markdown("## Control Panel")

if st.sidebar.button("Rerun Pipeline (Dry Run)"):
    st.sidebar.write("Triggering pipeline...")
    os.system("python pipeline.py")
    st.sidebar.success("Pipeline executed.")