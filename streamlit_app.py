import streamlit as st
import pandas as pd
import plotly.express as px
from io import StringIO
from datetime import datetime, timedelta
import re

# --------------------------------------------------
# Page Config
# --------------------------------------------------
st.set_page_config(
    page_title="Tokyo Trip Comparator",
    page_icon="✈️",
    layout="wide"
)

# --------------------------------------------------
# Password Gate
# --------------------------------------------------
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if st.session_state.password_correct:
        return True

    st.title("🔐 Tokyo Trip Comparator")
    st.caption("Enter the password to access the app.")

    password = st.text_input("Password", type="password")

    if st.button("Enter"):
        try:
            correct_password = st.secrets["APP_PASSWORD"]
        except KeyError:
            st.error("APP_PASSWORD is missing from Streamlit Cloud Secrets.")
            return False

        if password == correct_password:
            st.session_state.password_correct = True
            st.rerun()
        else:
            st.error("Incorrect password.")

    return False


if not check_password():
    st.stop()

# --------------------------------------------------
# App Header
# --------------------------------------------------
st.title("✈️ Tokyo Trip Comparator")
st.caption("Compare flight options by cost, timing, hotel impact, and split payments.")

# --------------------------------------------------
# Sidebar Controls
# --------------------------------------------------
DEFAULT_YEAR = st.sidebar.number_input(
    "Trip year",
    min_value=2026,
    max_value=2035,
    value=2027,
    step=1
)

st.sidebar.markdown("---")
st.sidebar.caption("Paste tab-separated data or upload a CSV/TSV.")

uploaded_file = st.sidebar.file_uploader(
    "Upload CSV or TSV",
    type=["csv", "tsv", "txt"]
)

# --------------------------------------------------
# Default Data
# --------------------------------------------------
sample_data = """Airline\tTravel Tier\tConnecting Outgoing Departure Date\tConnecting Outgoing Arrival Date\tOutgoing Departure Date\tOutgoing Arrival Date\tIncoming Departure Date\tIncoming Arrival Date\tConnecting Incoming Departure Date\tConnecting Incoming  Arrival Date\tHotel Check In\tHotel Check Out\tConnecting Outgoing Hotel Check In\tConnecting Outgoing Hotel Check Out\tConnecting Incoing Hotel Check In\tConnecting Incoing Hotel Check Out\tConnecting Hotel Price Max\tHypothetical Hotel Price Max\tConnecting Hotel Check In\tConnecting Hotel Check Out\tDirect Flight Price\tConnecting Flight Price\tFlight Price\tPer Person\t70/30 Split Daniel\t70/30 Split Kelsey\t$ of Highest Savings\tPercent of Highest Savings\tHotel + Flight\tPer Person\t70/30 Split Daniel\t70/30 Split Kelsey
Japan Airlines (Chicago)\tPremium Economy\t2/6 14:10\t2/6 16:21\t2/6 15:40\t2/7 22:00\t2/17 10:50\t2/17 7:35\t2/17 9:25\t2/17 13:10\t2/7\t2/17\t\t\t\t\t\t$4,589.60\t\t\t$4,193.06\t\t$4,193.06\t$2,096.53\t$2,935.14\t$1,257.92\t$6,775.94\t61.77%\t$8,782.66\t$4,391.33\t$6,147.86\t$2,634.80
Delta (Minniapolis)\tPremium Economy\t2/6 6:40\t2/6 9:16\t2/6 10:45\t2/7 14:35\t2/17 16:45\t2/17 14:55\t2/17 16:55\t2/17 14:26\t2/7\t2/17\t\t\t\t\t\t$4,589.60\t\t\t$4,483.85\t\t$4,483.85\t$2,241.93\t$3,138.70\t$1,345.16\t$6,485.15\t59.12%\t$9,073.45\t$4,536.73\t$6,351.42\t$2,722.04
Zipair (San Fransisco)\t"Business" Class\t2/5 6:00\t2/5 16:01\t2/6 15:45\t2/7 19:55\t2/17 21:25\t2/17 19:55\t2/18 6:00\t2/18 12:36\t2/7\t2/17\t2/5\t2/6\t2/17\t2/18\t$410.00\t$4,999.60\t2/6\t2/18\t$6,786.76\t$1,076.48\t$7,863.24\t$3,931.62\t$5,504.27\t$2,358.97\t$3,105.76\t28.31%\t$11,786.36\t$5,893.18\t$8,250.45\t$3,535.91
Japan Airlines (Chicago)\tBusiness Class\t2/6 14:10\t2/6 16:21\t2/6 15:40\t2/7 22:00\t2/17 10:50\t2/17 7:35\t2/17 9:25\t2/17 13:10\t2/7\t2/17\t\t\t\t\t\t$4,589.60\t\t\t$10,969.00\t\t$10,969.00\t$5,484.50\t$7,678.30\t$3,290.70\t$0.00\t\t$15,558.60\t$7,779.30\t$10,891.02\t$4,667.58
"""

with st.expander("Paste / edit trip data", expanded=False):
    pasted_data = st.text_area(
        "Trip data",
        value=sample_data,
        height=260
    )

# --------------------------------------------------
# Helper Functions
# --------------------------------------------------
def clean_money(value):
    if pd.isna(value) or str(value).strip() == "":
        return None

    cleaned = re.sub(r"[^0-9.\-]", "", str(value))

    if cleaned == "":
        return None

    return float(cleaned)


def clean_percent(value):
    if pd.isna(value) or str(value).strip() == "":
        return None

    cleaned = str(value).replace("%", "").strip()

    if cleaned == "":
        return None

    return float(cleaned)


def parse_trip_datetime(value, year):
    if pd.isna(value) or str(value).strip() == "":
        return pd.NaT

    text = str(value).strip()

    try:
        if ":" in text:
            return datetime.strptime(f"{year}/{text}", "%Y/%m/%d %H:%M")

        return datetime.strptime(f"{year}/{text}", "%Y/%m/%d")

    except ValueError:
        return pd.NaT


def fmt_money(value):
    if pd.isna(value) or value is None:
        return "—"

    return f"${value:,.2f}"


def fmt_pct(value):
    if pd.isna(value) or value is None:
        return "—"

    return f"{value:.2f}%"


def read_data():
    if uploaded_file is not None:
        content = uploaded_file.read().decode("utf-8")
    else:
        content = pasted_data

    if "\t" in content:
        return pd.read_csv(StringIO(content), sep="\t")

    return pd.read_csv(StringIO(content))


def make_short_option_label(airline, travel_tier):
    airline = str(airline).strip()
    travel_tier = str(travel_tier).strip().replace('"', "")

    # Remove airport/city note in parentheses
    airline_clean = re.sub(r"\s*\(.*?\)", "", airline).strip()

    airline_map = {
        "Japan Airlines": "JAL",
        "Zipair": "ZIPAIR",
        "ZIPAIR": "ZIPAIR",
        "Delta": "Delta",
    }

    tier_map = {
        "Premium Economy": "Prem Econ",
        "Business Class": "Business",
        "Business": "Business",
    }

    short_airline = airline_map.get(airline_clean, airline_clean)
    short_tier = tier_map.get(travel_tier, travel_tier)

    return f"{short_airline} — {short_tier}"


def normalize_columns(df):
    """
    Handles:
    - typo cleanup
    - duplicate pandas columns like Per Person and Per Person.1
    - double spaces in headers
    """
    df.columns = [str(c).strip().replace("  ", " ") for c in df.columns]

    rename_map = {
        # Common typo fixes
        "Connecting Outgoing Arival Date": "Connecting Outgoing Arrival Date",
        "Outgoing Arival Date": "Outgoing Arrival Date",
        "Incoing Departure Date": "Incoming Departure Date",
        "Incoing Arival Date": "Incoming Arrival Date",

        # New incoming connector fields
        "Connecting Incoming Arival Date": "Connecting Incoming Arrival Date",
        "Connecting Incoming Arrival Date.1": "Connecting Incoming Arrival Date",

        # Your current typo spelling
        "Connecting Incoing Hotel Check In": "Connecting Incoming Hotel Check In",
        "Connecting Incoing Hotel Check Out": "Connecting Incoming Hotel Check Out",

        # Old naming support
        "Connecting Return Departure Date": "Connecting Incoming Departure Date",
        "Connecting Return Arrival Date": "Connecting Incoming Arrival Date",
        "Connecting Return Arival Date": "Connecting Incoming Arrival Date",

        # Duplicate cost columns from pandas
        "Per Person": "Per Person Flight",
        "Per Person.1": "Per Person Total",
        "70/30 Split Daniel": "70/30 Split Daniel Flight",
        "70/30 Split Daniel.1": "70/30 Split Daniel Total",
        "70/30 Split Kelsey": "70/30 Split Kelsey Flight",
        "70/30 Split Kelsey.1": "70/30 Split Kelsey Total",
    }

    df = df.rename(columns=rename_map)
    return df


# --------------------------------------------------
# Load + Clean Data
# --------------------------------------------------
try:
    df = read_data()
except Exception as e:
    st.error(f"Could not read data: {e}")
    st.stop()

df = normalize_columns(df)

money_cols = [
    "Connecting Hotel Price Max",
    "Hypothetical Hotel Price Max",
    "Direct Flight Price",
    "Connecting Flight Price",
    "Flight Price",
    "Per Person Flight",
    "70/30 Split Daniel Flight",
    "70/30 Split Kelsey Flight",
    "$ of Highest Savings",
    "Hotel + Flight",
    "Per Person Total",
    "70/30 Split Daniel Total",
    "70/30 Split Kelsey Total",
]

for col in money_cols:
    if col in df.columns:
        df[col] = df[col].apply(clean_money)

if "Percent of Highest Savings" in df.columns:
    df["Percent of Highest Savings"] = df["Percent of Highest Savings"].apply(clean_percent)

date_cols = [
    "Connecting Outgoing Departure Date",
    "Connecting Outgoing Arrival Date",
    "Outgoing Departure Date",
    "Outgoing Arrival Date",
    "Incoming Departure Date",
    "Incoming Arrival Date",
    "Connecting Incoming Departure Date",
    "Connecting Incoming Arrival Date",
    "Hotel Check In",
    "Hotel Check Out",
    "Connecting Outgoing Hotel Check In",
    "Connecting Outgoing Hotel Check Out",
    "Connecting Incoming Hotel Check In",
    "Connecting Incoming Hotel Check Out",
    "Connecting Hotel Check In",
    "Connecting Hotel Check Out",
]

for col in date_cols:
    if col in df.columns:
        df[col] = df[col].apply(lambda x: parse_trip_datetime(x, DEFAULT_YEAR))

required_cols = ["Airline", "Travel Tier"]

for col in required_cols:
    if col not in df.columns:
        st.error(f"Missing required column: {col}")
        st.stop()

df["Option"] = df["Airline"].astype(str) + " — " + df["Travel Tier"].astype(str)
df["Short Option"] = df.apply(
    lambda row: make_short_option_label(row["Airline"], row["Travel Tier"]),
    axis=1
)

# --------------------------------------------------
# Trip Option Cards
# --------------------------------------------------
st.markdown("## 🧾 Trip Options")

sort_options = [
    "Hotel + Flight",
    "Flight Price",
    "Per Person Total",
    "$ of Highest Savings",
    "Percent of Highest Savings",
]

available_sort_options = [c for c in sort_options if c in df.columns]

sort_choice = st.selectbox(
    "Sort options by",
    available_sort_options,
    index=0 if available_sort_options else None
)

if sort_choice:
    ascending = sort_choice not in ["$ of Highest Savings", "Percent of Highest Savings"]
    df_display = df.sort_values(sort_choice, ascending=ascending, na_position="last")
else:
    df_display = df.copy()

card_cols = st.columns(2)

for i, (_, row) in enumerate(df_display.iterrows()):
    with card_cols[i % 2]:
        airline = row.get("Airline", "Unknown Airline")
        tier = row.get("Travel Tier", "Unknown Tier")

        st.markdown(
            f"""
            <div style="
                border: 1px solid rgba(120,120,120,0.35);
                border-radius: 16px;
                padding: 18px;
                margin-bottom: 16px;
                background: rgba(250,250,250,0.04);
            ">
                <h3 style="margin-bottom: 4px;">{airline}</h3>
                <p style="margin-top: 0; opacity: .75;">{tier}</p>
                <hr>
                <b>Flight Price:</b> {fmt_money(row.get("Flight Price"))}<br>
                <b>Flight Per Person:</b> {fmt_money(row.get("Per Person Flight"))}<br>
                <b>Hotel + Flight:</b> {fmt_money(row.get("Hotel + Flight"))}<br>
                <b>Total Per Person:</b> {fmt_money(row.get("Per Person Total"))}<br>
                <b>Daniel 70% Total:</b> {fmt_money(row.get("70/30 Split Daniel Total"))}<br>
                <b>Kelsey 30% Total:</b> {fmt_money(row.get("70/30 Split Kelsey Total"))}<br>
                <b>Savings:</b> {fmt_money(row.get("$ of Highest Savings"))} / {fmt_pct(row.get("Percent of Highest Savings"))}
            </div>
            """,
            unsafe_allow_html=True
        )

# --------------------------------------------------
# Cost Comparison
# --------------------------------------------------
st.markdown("---")
st.markdown("## 📊 Cost Comparison")

cost_options = [
    "Hotel + Flight",
    "Flight Price",
    "Per Person Flight",
    "Per Person Total",
    "70/30 Split Daniel Flight",
    "70/30 Split Daniel Total",
    "70/30 Split Kelsey Flight",
    "70/30 Split Kelsey Total",
    "$ of Highest Savings",
]

available_cost_options = [c for c in cost_options if c in df.columns]

cost_metric = st.selectbox(
    "Chart cost metric",
    available_cost_options,
    index=0 if available_cost_options else None
)

if cost_metric:
    chart_df = df.copy()

    fig_cost = px.bar(
        chart_df.sort_values(cost_metric),
        x=cost_metric,
        y="Option",
        orientation="h",
        text=cost_metric,
        title=f"{cost_metric} by Option"
    )

    fig_cost.update_traces(
        texttemplate="$%{text:,.0f}",
        textposition="outside"
    )

    fig_cost.update_layout(
        height=420,
        xaxis_title="Cost",
        yaxis_title="Trip Option"
    )

    st.plotly_chart(fig_cost, use_container_width=True)

# --------------------------------------------------
# Timeline
# --------------------------------------------------
st.markdown("---")
st.markdown("## 🗓️ Visual Trip Timeline")


def build_timeline_rows(source_df):
    rows = []

    for _, row in source_df.iterrows():
        option = row["Short Option"]
        full_option = row["Option"]

        timeline_parts = [
            (
                "Connector Outbound Flight",
                row.get("Connecting Outgoing Departure Date"),
                row.get("Connecting Outgoing Arrival Date"),
            ),
            (
                "Connector Outbound Hotel",
                row.get("Connecting Outgoing Hotel Check In"),
                row.get("Connecting Outgoing Hotel Check Out"),
            ),
            (
                "Main Outbound Flight",
                row.get("Outgoing Departure Date"),
                row.get("Outgoing Arrival Date"),
            ),
            (
                "Tokyo Hotel",
                row.get("Hotel Check In"),
                row.get("Hotel Check Out"),
            ),
            (
                "Return Flight",
                row.get("Incoming Departure Date"),
                row.get("Incoming Arrival Date"),
            ),
            (
                "Connector Incoming Hotel",
                row.get("Connecting Incoming Hotel Check In"),
                row.get("Connecting Incoming Hotel Check Out"),
            ),
            (
                "Connector Incoming Flight",
                row.get("Connecting Incoming Departure Date"),
                row.get("Connecting Incoming Arrival Date"),
            ),
            (
                "Connector Hotel / Full Buffer",
                row.get("Connecting Hotel Check In"),
                row.get("Connecting Hotel Check Out"),
            ),
        ]

        for segment, start, end in timeline_parts:
            if pd.notna(start) and pd.notna(end):
                if start == end:
                    end = start + timedelta(hours=12)

                rows.append(
                    {
                        "Option": option,
                        "Full Option": full_option,
                        "Segment": segment,
                        "Start": start,
                        "End": end,
                    }
                )

    return pd.DataFrame(rows)


timeline_df = build_timeline_rows(df)

if not timeline_df.empty:
    selected_options = st.multiselect(
        "Show options",
        sorted(timeline_df["Option"].unique()),
        default=sorted(timeline_df["Option"].unique())
    )

    timeline_filtered = timeline_df[timeline_df["Option"].isin(selected_options)]

    fig_timeline = px.timeline(
        timeline_filtered,
        x_start="Start",
        x_end="End",
        y="Option",
        color="Segment",
        hover_data={
            "Full Option": True,
            "Segment": True,
            "Start": True,
            "End": True,
            "Option": False,
        },
        title="Trip Timeline"
    )

    fig_timeline.update_yaxes(
        autorange="reversed",
        title="",
    )

    fig_timeline.update_layout(
    height=650,
    xaxis_title="Date / Time",
    yaxis_title="",
    legend_title="",
    legend=dict(
        orientation="h",
        yanchor="top",
        y=-0.18,
        xanchor="center",
        x=0.5,
        ),
        margin=dict(l=20, r=20, t=60, b=120),
    )

    st.plotly_chart(fig_timeline, use_container_width=True)
else:
    st.info("No timeline data found. Check that date columns are filled correctly.")

# --------------------------------------------------
# Calendar Notes
# --------------------------------------------------
st.markdown("---")
st.markdown("## 📅 Day-by-Day Calendar Notes")


def add_calendar_event(events, date_value, option, label):
    if pd.notna(date_value):
        events.append(
            {
                "Date": date_value.date(),
                "Time": date_value.strftime("%I:%M %p").lstrip("0"),
                "Option": option,
                "Plan": label,
            }
        )


calendar_events = []

for _, row in df.iterrows():
    option = row["Option"]

    add_calendar_event(
        calendar_events,
        row.get("Connecting Outgoing Departure Date"),
        option,
        "Connector outbound flight departs"
    )

    add_calendar_event(
        calendar_events,
        row.get("Connecting Outgoing Arrival Date"),
        option,
        "Connector outbound flight arrives"
    )

    add_calendar_event(
        calendar_events,
        row.get("Connecting Outgoing Hotel Check In"),
        option,
        "Connector outbound hotel check-in"
    )

    add_calendar_event(
        calendar_events,
        row.get("Connecting Outgoing Hotel Check Out"),
        option,
        "Connector outbound hotel check-out"
    )

    add_calendar_event(
        calendar_events,
        row.get("Outgoing Departure Date"),
        option,
        "Main outbound flight departs"
    )

    add_calendar_event(
        calendar_events,
        row.get("Outgoing Arrival Date"),
        option,
        "Arrive in Tokyo"
    )

    add_calendar_event(
        calendar_events,
        row.get("Hotel Check In"),
        option,
        "Tokyo hotel check-in"
    )

    add_calendar_event(
        calendar_events,
        row.get("Hotel Check Out"),
        option,
        "Tokyo hotel check-out"
    )

    add_calendar_event(
        calendar_events,
        row.get("Incoming Departure Date"),
        option,
        "Return flight departs"
    )

    add_calendar_event(
        calendar_events,
        row.get("Incoming Arrival Date"),
        option,
        "Return flight arrives"
    )

    add_calendar_event(
        calendar_events,
        row.get("Connecting Incoming Hotel Check In"),
        option,
        "Connector incoming hotel check-in"
    )

    add_calendar_event(
        calendar_events,
        row.get("Connecting Incoming Hotel Check Out"),
        option,
        "Connector incoming hotel check-out"
    )

    add_calendar_event(
        calendar_events,
        row.get("Connecting Incoming Departure Date"),
        option,
        "Connector incoming flight departs"
    )

    add_calendar_event(
        calendar_events,
        row.get("Connecting Incoming Arrival Date"),
        option,
        "Final arrival home"
    )

calendar_df = pd.DataFrame(calendar_events)

if not calendar_df.empty:
    calendar_df = calendar_df.sort_values(["Date", "Time", "Option"])

    selected_calendar_options = st.multiselect(
        "Calendar options",
        sorted(calendar_df["Option"].unique()),
        default=sorted(calendar_df["Option"].unique())
    )

    calendar_df = calendar_df[calendar_df["Option"].isin(selected_calendar_options)]

    for date, group in calendar_df.groupby("Date"):
        st.markdown(f"### {date.strftime('%A, %B %d, %Y')}")
        st.dataframe(
            group[["Time", "Option", "Plan"]],
            use_container_width=True,
            hide_index=True
        )
else:
    st.info("No calendar events found.")

# --------------------------------------------------
# Simple Decision Helper
# --------------------------------------------------
st.markdown("---")
st.markdown("## 🧠 Quick Decision Helper")

helper_cols = st.columns(4)

with helper_cols[0]:
    if "Hotel + Flight" in df.columns and df["Hotel + Flight"].notna().any():
        cheapest_total = df.loc[df["Hotel + Flight"].idxmin()]
        st.metric(
            "Cheapest Total",
            cheapest_total["Airline"],
            fmt_money(cheapest_total["Hotel + Flight"])
        )

with helper_cols[1]:
    if "Flight Price" in df.columns and df["Flight Price"].notna().any():
        cheapest_flight = df.loc[df["Flight Price"].idxmin()]
        st.metric(
            "Cheapest Flight",
            cheapest_flight["Airline"],
            fmt_money(cheapest_flight["Flight Price"])
        )

with helper_cols[2]:
    if "Per Person Total" in df.columns and df["Per Person Total"].notna().any():
        best_pp = df.loc[df["Per Person Total"].idxmin()]
        st.metric(
            "Lowest Per Person",
            best_pp["Airline"],
            fmt_money(best_pp["Per Person Total"])
        )

with helper_cols[3]:
    if "$ of Highest Savings" in df.columns and df["$ of Highest Savings"].notna().any():
        best_savings = df.loc[df["$ of Highest Savings"].idxmax()]
        st.metric(
            "Highest Savings",
            best_savings["Airline"],
            fmt_money(best_savings["$ of Highest Savings"])
        )

# --------------------------------------------------
# Raw Data
# --------------------------------------------------
st.markdown("---")
st.markdown("## 🔍 Raw Cleaned Data")

with st.expander("View cleaned table"):
    st.dataframe(df, use_container_width=True)