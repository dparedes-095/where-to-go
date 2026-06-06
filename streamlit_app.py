import streamlit as st
import pandas as pd
import plotly.express as px
import streamlit.components.v1 as components
from io import StringIO
from datetime import datetime, timedelta
import re
import calendar

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
sample_data = """Airline\tTravel Tier\tConnecting Outgoing Departure Date\tConnecting Outgoing Arrival Date\tOutgoing Departure Date\tOutgoing Arrival Date\tIncoming Departure Date\tIncoming Arrival Date\tConnecting Incoming Departure Date\tConnecting Incoming  Arrival Date\tHotel Check In\tHotel Check Out\tConnecting Outgoing Hotel Check In\tConnecting Outgoing Hotel Check Out\tConnecting Incoming Hotel Check In\tConnecting Incoming Hotel Check Out\tConnecting Hotel Price Max\tHypothetical Hotel Price Max\tDirect Flight Price\tAMEX Discount\tDirect Flight Price (Discounted)\tConnecting Flight Price\tFlight Price\tPer Person\t70/30 Split Daniel\t70/30 Split Kelsey\t$ of Highest Savings\tPercent of Highest Savings\tHotel + Flight\tPer Person\t70/30 Split Daniel\t70/30 Split Kelsey
Japan Airlines (Chicago)\tPremium Economy\t2/6 14:10\t2/6 16:21\t2/6 17:40\t2/7 22:00\t2/17 10:50\t2/17 7:35\t2/17 9:25\t2/17 13:10\t2/7\t2/17\t\t\t\t\t\t$4,589.60\t$4,853.06\t$660.00\t$4,193.06\t\t$4,193.06\t$2,096.53\t$2,935.14\t$1,257.92\t$6,775.94\t61.77%\t$8,782.66\t$4,391.33\t$6,147.86\t$2,634.80
Delta (Minneapolis)\tPremium Economy\t2/6 6:40\t2/6 9:16\t2/6 10:45\t2/7 14:35\t2/17 16:45\t2/17 14:55\t2/17 16:55\t2/17 14:26\t2/7\t2/17\t\t\t\t\t\t$4,589.60\t$5,143.85\t$660.00\t$4,483.85\t\t$4,483.85\t$2,241.93\t$3,138.70\t$1,345.16\t$6,485.15\t59.12%\t$9,073.45\t$4,536.73\t$6,351.42\t$2,722.04
Zipair (San Francisco)\t"Business" Class\t2/6 7:10\t2/6 12:55\t2/6 15:45\t2/7 19:55\t2/17 21:25\t2/17 19:55\t2/17 23:10\t2/18 11:25\t2/7\t2/17\t\t\t2/17\t2/18\t$0.00\t$4,589.60\t$6,786.76\t\t$6,786.76\t$1,132.80\t$7,919.56\t$3,959.78\t$5,543.69\t$2,375.87\t$3,049.44\t27.80%\t$11,376.36\t$5,688.18\t$7,963.45\t$3,412.91
Japan Airlines (Chicago)\tMixed JAL\t\t\t2/6 17:40\t2/7 22:00\t2/17 17:00\t2/17 13:40\t\t\t2/7\t2/17\t\t\t\t\t\t$4,589.60\t$7,681.00\t$660.00\t$7,021.00\t\t$7,021.00\t$3,510.50\t$4,914.70\t$2,106.30\t$3,948.00\t35.99%\t$11,610.60\t$5,805.30\t$8,127.42\t$3,483.18
Japan/ZIP Airlines (Chicago/San Francisco)\tBusiness Class\t2/6 7:10\t2/6 12:55\t2/6 15:45\t2/7 19:55\t2/17 17:00\t2/17 13:40\t\t\t2/7\t2/17\t\t\t\t\t\t$4,589.60\t$8,349.00\t$660.00\t$7,689.00\t$546.40\t$8,235.40\t$4,117.70\t$5,764.78\t$2,470.62\t$2,733.60\t24.92%\t$12,278.60\t$6,139.30\t$8,595.02\t$3,683.58
Japan Airlines (Seattle)\tBusiness Class\t2/3 18:30\t2/3 21:58\t2/4 11:55\t2/5 15:05\t2/16 18:10\t2/16 9:55\t2/17 8:40\t2/17 17:16\t2/5\t2/16\t2/3\t2/4\t2/16\t2/17\t$260.00\t$4,849.60\t$6,094.00\t$660.00\t$5,434.00\t$1,091.00\t$6,525.00\t$3,262.50\t$4,567.50\t$1,957.50\t$4,444.00\t40.51%\t$10,283.60\t$5,141.80\t$7,198.52\t$3,085.08
Japan Airlines (Chicago)\tBusiness Class\t2/6 14:10\t2/6 16:21\t2/6 17:40\t2/7 22:00\t2/17 10:50\t2/17 7:35\t2/17 9:25\t2/17 13:10\t2/7\t2/17\t\t\t\t\t\t$4,589.60\t$11,629.00\t$660.00\t$10,969.00\t\t$10,969.00\t$5,484.50\t$7,678.30\t$3,290.70\t$0.00\t0.00%\t$15,558.60\t$7,779.30\t$10,891.02\t$4,667.58
Delta (Dallas)\tFirst Class\t2/4 8:30\t2/4 11:11\t2/4 14:15\t2/5 17:45\t2/16 16:50\t2/16 14:55\t2/16 20:05\t2/16 21:38\t2/5\t2/16\t\t\t\t\t\t$4,589.60\t$10,722.00\t$660.00\t$10,062.00\t\t$10,062.00\t$5,031.00\t$7,043.40\t$3,018.60\t$907.00\t8.27%\t$14,651.60\t$7,325.80\t$10,256.12\t$4,395.48
"""

with st.expander("Paste / edit trip data", expanded=False):
    pasted_data = st.text_area(
        "Trip data",
        value=sample_data,
        height=260,
        key="trip_data_v9"
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

    airline_clean = re.sub(r"\s*\(.*?\)", "", airline).strip()

    location_match = re.search(r"\((.*?)\)", airline)
    location = location_match.group(1).strip() if location_match else ""

    airline_map = {
        "Japan Airlines": "JAL",
        "Zipair": "ZIPAIR",
        "ZIPAIR": "ZIPAIR",
        "Delta": "Delta",
        "Japan/ZIP Airlines": "JAL/ZIP",
    }

    location_map = {
        "Chicago": "CHI",
        "Seattle": "SEA",
        "San Francisco": "SFO",
        "Minneapolis": "MSP",
        "Dallas": "DAL",
        "Chicago/San Francisco": "CHI/SFO",
    }

    tier_map = {
        "Premium Economy": "Prem Econ",
        "Business Class": "Business",
        "Business": "Business",
        "Mixed": "Mixed",
        "Mixed JAL": "Mixed JAL",
        "First Class": "First",
    }

    short_airline = airline_map.get(airline_clean, airline_clean)
    short_location = location_map.get(location, location)
    short_tier = tier_map.get(travel_tier, travel_tier)

    if short_location:
        return f"{short_airline} {short_location} — {short_tier}"

    return f"{short_airline} — {short_tier}"


def normalize_columns(df):
    df.columns = [str(c).strip().replace("  ", " ") for c in df.columns]

    # Drop blank/extra pasted columns like Unnamed: 34, Unnamed: 35, etc.
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]

    rename_map = {
        "Connecting Outgoing Arival Date": "Connecting Outgoing Arrival Date",
        "Outgoing Arival Date": "Outgoing Arrival Date",
        "Incoing Departure Date": "Incoming Departure Date",
        "Incoing Arival Date": "Incoming Arrival Date",
        "Connecting Incoming Arival Date": "Connecting Incoming Arrival Date",
        "Connecting Incoming Arrival Date.1": "Connecting Incoming Arrival Date",
        "Connecting Return Departure Date": "Connecting Incoming Departure Date",
        "Connecting Return Arrival Date": "Connecting Incoming Arrival Date",
        "Connecting Return Arival Date": "Connecting Incoming Arrival Date",
        "Per Person": "Per Person Flight",
        "Per Person.1": "Per Person Total",
        "70/30 Split Daniel": "70/30 Split Daniel Flight",
        "70/30 Split Daniel.1": "70/30 Split Daniel Total",
        "70/30 Split Kelsey": "70/30 Split Kelsey Flight",
        "70/30 Split Kelsey.1": "70/30 Split Kelsey Total",
    }

    return df.rename(columns=rename_map)


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
    "AMEX Discount",
    "Direct Flight Price (Discounted)",
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
# Main App Tabs
# --------------------------------------------------
overview_tab, hotel_tab, raw_tab = st.tabs([
    "✈️ Trip Comparator",
    "🏨 Hotel Calendar",
    "🔍 Raw Data",
])

with overview_tab:
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
    # Trip-Specific Calendar Notes
    # --------------------------------------------------
    st.markdown("---")
    st.markdown("## 📅 Trip Day-by-Day Plan")

    st.caption("Pick one trip option to see a cleaner day-by-day itinerary.")

    trip_options = df["Short Option"].tolist()

    selected_trip = st.selectbox(
        "Choose trip option",
        trip_options,
        index=0
    )

    selected_row = df[df["Short Option"] == selected_trip].iloc[0]

    st.markdown(f"### {selected_row['Option']}")


    def add_trip_event(events, date_value, label, category, sort_order, display_time=None):
        if pd.notna(date_value):
            events.append(
                {
                    "Date": date_value.date(),
                    "Time": display_time if display_time else date_value.strftime("%I:%M %p").lstrip("0"),
                    "Plan": label,
                    "Category": category,
                    "Sort Order": sort_order,
                }
            )


    def get_category_style(category):
        styles = {
            "Connector Flight": {
                "border": "#3b82f6",
                "background": "rgba(59, 130, 246, 0.12)",
                "badge_bg": "rgba(59, 130, 246, 0.22)",
            },
            "Main Flight": {
                "border": "#8b5cf6",
                "background": "rgba(139, 92, 246, 0.12)",
                "badge_bg": "rgba(139, 92, 246, 0.22)",
            },
            "Connector Hotel": {
                "border": "#f59e0b",
                "background": "rgba(245, 158, 11, 0.12)",
                "badge_bg": "rgba(245, 158, 11, 0.22)",
            },
            "Tokyo Stay": {
                "border": "#22c55e",
                "background": "rgba(34, 197, 94, 0.12)",
                "badge_bg": "rgba(34, 197, 94, 0.22)",
            },
        }

        return styles.get(
            category,
            {
                "border": "rgba(120,120,120,0.35)",
                "background": "rgba(250,250,250,0.035)",
                "badge_bg": "rgba(250,250,250,0.08)",
            },
        )


    trip_events = []

    add_trip_event(
        trip_events,
        selected_row.get("Connecting Outgoing Departure Date"),
        "Connector outbound flight departs",
        "Connector Flight",
        10
    )

    add_trip_event(
        trip_events,
        selected_row.get("Connecting Outgoing Arrival Date"),
        "Connector outbound flight arrives",
        "Connector Flight",
        20
    )

    add_trip_event(
        trip_events,
        selected_row.get("Connecting Outgoing Hotel Check In"),
        "Connector outbound hotel check-in",
        "Connector Hotel",
        30,
        "Check-in day"
    )

    add_trip_event(
        trip_events,
        selected_row.get("Connecting Outgoing Hotel Check Out"),
        "Connector outbound hotel check-out",
        "Connector Hotel",
        40,
        "Check-out day"
    )

    add_trip_event(
        trip_events,
        selected_row.get("Outgoing Departure Date"),
        "Main outbound flight departs",
        "Main Flight",
        50
    )

    add_trip_event(
        trip_events,
        selected_row.get("Outgoing Arrival Date"),
        "Arrive in Tokyo",
        "Main Flight",
        60
    )

    add_trip_event(
        trip_events,
        selected_row.get("Hotel Check In"),
        "Tokyo hotel check-in",
        "Tokyo Stay",
        70,
        "Check-in day"
    )

    add_trip_event(
        trip_events,
        selected_row.get("Hotel Check Out"),
        "Tokyo hotel check-out",
        "Tokyo Stay",
        80,
        "Check-out day"
    )

    add_trip_event(
        trip_events,
        selected_row.get("Incoming Departure Date"),
        "Return flight departs",
        "Main Flight",
        90
    )

    add_trip_event(
        trip_events,
        selected_row.get("Incoming Arrival Date"),
        "Return flight arrives",
        "Main Flight",
        100
    )

    add_trip_event(
        trip_events,
        selected_row.get("Connecting Incoming Hotel Check In"),
        "Connector incoming hotel check-in",
        "Connector Hotel",
        110,
        "Check-in day"
    )

    add_trip_event(
        trip_events,
        selected_row.get("Connecting Incoming Hotel Check Out"),
        "Connector incoming hotel check-out",
        "Connector Hotel",
        120,
        "Check-out day"
    )

    add_trip_event(
        trip_events,
        selected_row.get("Connecting Incoming Departure Date"),
        "Connector incoming flight departs",
        "Connector Flight",
        130
    )

    add_trip_event(
        trip_events,
        selected_row.get("Connecting Incoming Arrival Date"),
        "Final arrival home",
        "Connector Flight",
        140
    )

    trip_calendar_df = pd.DataFrame(trip_events)

    if not trip_calendar_df.empty:
        trip_calendar_df = trip_calendar_df.sort_values(["Date", "Sort Order"])

        summary_cols = st.columns(4)

        with summary_cols[0]:
            st.metric(
                "Flight Price",
                fmt_money(selected_row.get("Flight Price"))
            )

        with summary_cols[1]:
            st.metric(
                "Hotel + Flight",
                fmt_money(selected_row.get("Hotel + Flight"))
            )

        with summary_cols[2]:
            st.metric(
                "Per Person Total",
                fmt_money(selected_row.get("Per Person Total"))
            )

        with summary_cols[3]:
            st.metric(
                "Savings",
                fmt_money(selected_row.get("$ of Highest Savings"))
            )

        st.markdown("#### Daily Plan")

        for date, group in trip_calendar_df.groupby("Date"):
            st.markdown(f"### {date.strftime('%A, %B %d, %Y')}")

            for _, event in group.iterrows():
                style = get_category_style(event["Category"])

                st.markdown(
                    f"""
                    <div style="
                        border-left: 6px solid {style["border"]};
                        border-top: 1px solid rgba(120,120,120,0.20);
                        border-right: 1px solid rgba(120,120,120,0.20);
                        border-bottom: 1px solid rgba(120,120,120,0.20);
                        border-radius: 12px;
                        padding: 12px 14px;
                        margin-bottom: 8px;
                        background: {style["background"]};
                    ">
                        <div style="
                            display: flex;
                            justify-content: space-between;
                            align-items: center;
                            gap: 12px;
                            margin-bottom: 5px;
                        ">
                            <div style="font-size: 0.85rem; opacity: 0.75;">
                                {event["Time"]}
                            </div>
                            <div style="
                                font-size: 0.75rem;
                                font-weight: 700;
                                padding: 3px 8px;
                                border-radius: 999px;
                                background: {style["badge_bg"]};
                                white-space: nowrap;
                            ">
                                {event["Category"]}
                            </div>
                        </div>
                        <div style="font-size: 1rem; font-weight: 600;">
                            {event["Plan"]}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    else:
        st.info("No calendar events found for this trip.")



with hotel_tab:
    st.markdown("## 🏨 Hotel Calendar")
    st.caption("Hotel-only card calendar for the Tokyo hotel split and Valentine’s Day Hilton stay.")

    # --------------------------------------------------
    # Editable Hotel / Trip Blocks
    # --------------------------------------------------
    # Prices are placeholders/planning values where noted.
    # End dates are shown on the calendar as checkout days.
    calendar_items = [
        {
            "Name": "Hilton",
            "Type": "Hotel",
            "Start": datetime(DEFAULT_YEAR, 2, 5, 11, 0),
            "End": datetime(DEFAULT_YEAR, 2, 8, 15, 0),
            "Price": 1128.94,
            "Label": "Hilton stay",
            "Subtext": "$1,128.94 total",
            "Emoji": "🏨",
            "Color": "hilton",
        },
        {
            "Name": "New City 1 Hotel",
            "Type": "Hotel Placeholder",
            "Start": datetime(DEFAULT_YEAR, 2, 8, 11, 0),
            "End": datetime(DEFAULT_YEAR, 2, 10, 15, 0),
            "Price": None,
            "Label": "New City 1 Hotel",
            "Subtext": "Placeholder • 2 nights",
            "Emoji": "🏙️",
            "Color": "city1",
        },
        {
            "Name": "New City 2 Hotel",
            "Type": "Hotel Placeholder",
            "Start": datetime(DEFAULT_YEAR, 2, 10, 11, 0),
            "End": datetime(DEFAULT_YEAR, 2, 13, 15, 0),
            "Price": None,
            "Label": "New City 2 Hotel",
            "Subtext": "Placeholder • 3 nights",
            "Emoji": "🌆",
            "Color": "city2",
        },
        {
            "Name": "Hilton",
            "Type": "Hotel",
            "Start": datetime(DEFAULT_YEAR, 2, 13, 11, 0),
            "End": datetime(DEFAULT_YEAR, 2, 16, 15, 0),
            "Price": 982.84,
            "Label": "Hilton stay",
            "Subtext": "$982.84 total",
            "Emoji": "🏨",
            "Color": "hilton2",
        },
    ]

    calendar_df = pd.DataFrame(calendar_items)
    calendar_df["Nights"] = calendar_df.apply(
        lambda row: max((row["End"].date() - row["Start"].date()).days, 0)
        if "Hotel" in row["Type"] else 0,
        axis=1,
    )
    calendar_df["Price / Night"] = calendar_df.apply(
        lambda row: row["Price"] / row["Nights"]
        if pd.notna(row["Price"]) and row["Nights"] else None,
        axis=1,
    )

    priced_hotels_df = calendar_df[
        (calendar_df["Type"].str.contains("Hotel")) &
        (calendar_df["Price"].notna())
    ].copy()

    total_known_hotel_cost = priced_hotels_df["Price"].sum()
    total_known_hotel_nights = int(priced_hotels_df["Nights"].sum())
    average_known_nightly = (
        total_known_hotel_cost / total_known_hotel_nights
        if total_known_hotel_nights else 0
    )
    hilton_total = priced_hotels_df[priced_hotels_df["Name"] == "Hilton"]["Price"].sum()

    metric_cols = st.columns(4)

    with metric_cols[0]:
        st.metric("Known hotel total", fmt_money(total_known_hotel_cost))

    with metric_cols[1]:
        st.metric("Known nights", total_known_hotel_nights)

    with metric_cols[2]:
        st.metric("Avg known nightly", fmt_money(average_known_nightly))

    with metric_cols[3]:
        st.metric("Known Hilton total", fmt_money(hilton_total))

    st.info(
        "Hilton is set at $982.84 total for 2/13–2/16. "
        "New City 1 and New City 2 are intentionally unpriced for now."
    )

    st.markdown("### February 2027 Overlay")

    # --------------------------------------------------
    # Calendar Helpers
    # --------------------------------------------------
    def fmt_hotel_time(value):
        return value.strftime("%I:%M %p").lstrip("0")

    def item_events_for_day(day_date):
        events = []

        for item in calendar_items:
            start_date = item["Start"].date()
            end_date = item["End"].date()

            if start_date <= day_date <= end_date:
                nights = max((end_date - start_date).days, 1)
                nightly = item["Price"] / nights if item["Price"] is not None else None

                if day_date == start_date:
                    status = f"Check in {fmt_hotel_time(item['Start'])}"
                elif day_date == end_date:
                    status = f"Check out {fmt_hotel_time(item['End'])}"
                else:
                    status = "Stay night"

                price_text = fmt_money(item["Price"]) if item["Price"] is not None else "Price TBD"
                nightly_text = f" • {fmt_money(nightly)}/night" if nightly is not None else ""

                events.append(
                    {
                        "text": f"{item['Emoji']} {item['Label']}",
                        "subtext": f"{status} • {price_text}{nightly_text}",
                        "color": item["Color"],
                        "status": status,
                    }
                )

        return events

    cal = calendar.Calendar(firstweekday=6)  # Sunday start
    month_days = cal.monthdatescalendar(DEFAULT_YEAR, 2)
    weekday_labels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

    calendar_html = """
    <style>
        .hotel-calendar-wrap {
            border: 1px solid rgba(148,163,184,0.34);
            border-radius: 18px;
            overflow: hidden;
            background: #0f172a;
            color: #f8fafc;
        }
        .hotel-calendar-header {
            display: grid;
            grid-template-columns: repeat(7, minmax(0, 1fr));
            border-bottom: 1px solid rgba(148,163,184,0.32);
            background: #111827;
            color: #f8fafc;
        }
        .hotel-weekday {
            padding: 10px 8px;
            text-align: center;
            font-size: 0.78rem;
            font-weight: 800;
            color: #cbd5e1;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }
        .hotel-calendar-grid {
            display: grid;
            grid-template-columns: repeat(7, minmax(0, 1fr));
        }
        .hotel-day {
            min-height: 146px;
            padding: 9px;
            border-right: 1px solid rgba(148,163,184,0.22);
            border-bottom: 1px solid rgba(148,163,184,0.22);
            position: relative;
            background: #0f172a;
            color: #f8fafc;
        }
        .hotel-day:nth-child(7n) {
            border-right: none;
        }
        .hotel-muted {
            opacity: 0.45;
        }
        .hotel-day-number {
            font-size: 0.9rem;
            font-weight: 800;
            margin-bottom: 7px;
            color: #f8fafc;
        }
        .hotel-pill {
            border-radius: 12px;
            padding: 8px 9px;
            margin-top: 6px;
            box-shadow: 0 10px 24px rgba(0,0,0,0.32);
            color: #ffffff;
        }
        .hotel-pill-main {
            font-weight: 850;
            font-size: 0.82rem;
            line-height: 1.2;
            color: #ffffff;
            text-shadow: 0 1px 1px rgba(0,0,0,0.28);
        }
        .hotel-pill-sub {
            margin-top: 4px;
            font-size: 0.70rem;
            line-height: 1.2;
            color: rgba(255,255,255,0.92);
        }
        .hotel-pill.hilton {
            border: 1px solid rgba(125,211,252,0.78);
            background: linear-gradient(135deg, #0369a1, #1d4ed8);
        }
        .hotel-pill.hilton2 {
            border: 1px solid rgba(103,232,249,0.78);
            background: linear-gradient(135deg, #0e7490, #2563eb);
        }
        .hotel-pill.city1 {
            border: 1px solid rgba(134,239,172,0.78);
            background: linear-gradient(135deg, #15803d, #0f766e);
        }
        .hotel-pill.city2 {
            border: 1px solid rgba(216,180,254,0.80);
            background: linear-gradient(135deg, #7e22ce, #be185d);
        }
        .hotel-pill.disney {
            border: 1px solid rgba(254,202,202,0.86);
            background: linear-gradient(135deg, #dc2626, #be123c);
        }
        .hotel-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 14px;
        }
        .hotel-chip {
            border: 1px solid rgba(148,163,184,0.34);
            border-radius: 999px;
            padding: 6px 10px;
            font-size: 0.78rem;
            background: #111827;
            color: #f8fafc;
        }
        @media (max-width: 760px) {
            .hotel-day {
                min-height: 122px;
                padding: 6px;
            }
            .hotel-pill {
                padding: 6px;
            }
            .hotel-pill-main {
                font-size: 0.72rem;
            }
            .hotel-pill-sub {
                font-size: 0.62rem;
            }
        }
    </style>
    <div class="hotel-chip-row">
        <div class="hotel-chip">🏨 Hilton</div>
        <div class="hotel-chip">🏙️ City placeholder</div>
        <div class="hotel-chip">🏨 Hilton Valentine’s stay</div>
    </div>
    <div class="hotel-calendar-wrap">
        <div class="hotel-calendar-header">
    """

    for label in weekday_labels:
        calendar_html += f'<div class="hotel-weekday">{label}</div>'

    calendar_html += '</div><div class="hotel-calendar-grid">'

    for week in month_days:
        for day in week:
            muted_class = " hotel-muted" if day.month != 2 else ""
            calendar_html += f'<div class="hotel-day{muted_class}">'
            calendar_html += f'<div class="hotel-day-number">{day.day}</div>'

            if day.month == 2:
                for event in item_events_for_day(day):
                    calendar_html += f"""
                    <div class="hotel-pill {event['color']}">
                        <div class="hotel-pill-main">{event['text']}</div>
                        <div class="hotel-pill-sub">{event['subtext']}</div>
                    </div>
                    """

            calendar_html += '</div>'

    calendar_html += '</div></div>'

    components.html(calendar_html, height=860, scrolling=False)

    # --------------------------------------------------
    # Details + Suggested Park Logic
    # --------------------------------------------------
    st.markdown("### Stay Details")

    details_df = calendar_df.copy()
    details_df["Check In / Start"] = details_df["Start"].dt.strftime("%a, Feb %-d • %-I:%M %p")
    details_df["Check Out / End"] = details_df["End"].dt.strftime("%a, Feb %-d • %-I:%M %p")
    details_df["Total"] = details_df["Price"].apply(fmt_money)
    details_df["Nightly"] = details_df["Price / Night"].apply(fmt_money)

    st.dataframe(
        details_df[[
            "Name",
            "Type",
            "Check In / Start",
            "Check Out / End",
            "Nights",
            "Total",
            "Nightly",
        ]],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### Hotel Flow Notes")

    note_cols = st.columns(3)

    with note_cols[0]:
        st.markdown(
            """
            **2/13 — Hilton check-in**  
            Move from New City 2 back to Hilton, bag drop/check in, then keep the evening flexible.
            """
        )

    with note_cols[1]:
        st.markdown(
            """
            **2/14 — Valentine’s Day**  
            Park-max day with Hilton as the stable base instead of a Disney hotel split.
            """
        )

    with note_cols[2]:
        st.markdown(
            """
            **2/15 — Hilton stay night**  
            No hotel move today. Cleaner logistics before the 2/16 checkout.
            """
        )


with raw_tab:
    # --------------------------------------------------
    # Raw Data
    # --------------------------------------------------
    st.markdown("---")
    st.markdown("## 🔍 Raw Cleaned Data")

    with st.expander("View cleaned table"):
        st.dataframe(df, use_container_width=True)
