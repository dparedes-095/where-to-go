import streamlit as st
import pandas as pd
import plotly.express as px
import streamlit.components.v1 as components
from io import StringIO
from datetime import datetime, timedelta
import re
import calendar
import json
import math
import os
from copy import deepcopy
from datetime import date
from html import escape
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

# --------------------------------------------------
# Page Config
# --------------------------------------------------
st.set_page_config(
    page_title="Tokyo Trip Comparator",
    page_icon="✈️",
    initial_sidebar_state="collapsed",
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
st.title("Japan itinerary")
st.caption("Orlando → Seattle → Tokyo · Japan Airlines Business Class")

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
st.sidebar.caption("Upload a CSV/TSV to use your own trip data.")

uploaded_file = st.sidebar.file_uploader(
    "Upload CSV or TSV",
    type=["csv", "tsv", "txt"]
)

# --------------------------------------------------
# Default Data
# --------------------------------------------------
sample_data = """Airline\tTravel Tier\tConnecting Outgoing Departure Date\tConnecting Outgoing Arrival Date\tOutgoing Departure Date\tOutgoing Arrival Date\tIncoming Departure Date\tIncoming Arrival Date\tConnecting Incoming Departure Date\tConnecting Incoming  Arrival Date\tHotel Check In\tHotel Check Out\tConnecting Outgoing Hotel Check In\tConnecting Outgoing Hotel Check Out\tConnecting Incoming Hotel Check In\tConnecting Incoming Hotel Check Out\tConnecting Hotel Price Max\tHypothetical Hotel Price Max\tDirect Flight Price\tAMEX Discount\tDirect Flight Price (Discounted)\tConnecting Flight Price\tFlight Price\tPer Person\t70/30 Split Daniel\t70/30 Split Kelsey\t$ of Highest Savings\tPercent of Highest Savings\tHotel + Flight\tPer Person\t70/30 Split Daniel\t70/30 Split Kelsey
Japan Airlines (Seattle)\tBusiness Class\t2/3 18:30\t2/3 21:58\t2/4 11:55\t2/5 15:05\t2/16 18:10\t2/16 9:55\t2/17 8:40\t2/17 17:16\t2/5\t2/16\t2/3\t2/4\t2/16\t2/17\t$260.00\t$4,849.60\t$6,094.00\t$660.00\t$5,434.00\t$1,091.00\t$6,525.00\t$3,262.50\t$4,567.50\t$1,957.50\t$4,444.00\t40.51%\t$10,283.60\t$5,141.80\t$7,198.52\t$3,085.08
"""

# --------------------------------------------------
# Helper Functions
# --------------------------------------------------
def clean_money(value):
    if pd.isna(value) or str(value).strip() == "":
        return None

    cleaned = re.sub(r"[^0-9.-]", "", str(value))

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
        content = sample_data

    if "\t" in content:
        return pd.read_csv(StringIO(content), sep="\t")

    return pd.read_csv(StringIO(content))


def normalize_columns(df):
    df.columns = [" ".join(str(c).split()) for c in df.columns]

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

required_cols = ["Airline", "Travel Tier"]

for col in required_cols:
    if col not in df.columns:
        st.error(f"Missing required column: {col}")
        st.stop()

chosen = (
    df["Airline"].astype(str).str.strip().str.casefold().eq("japan airlines (seattle)")
    & df["Travel Tier"].astype(str).str.strip().str.casefold().eq("business class")
)
df = df.loc[chosen].copy()
if len(df) != 1:
    st.error("Trip data must contain exactly one Japan Airlines (Seattle) Business Class row.")
    st.stop()
df["Option"] = "Japan Airlines Business Class — Orlando via Seattle to Tokyo"
df["Short Option"] = "JAL SEA — Business"

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

# --------------------------------------------------
option = st.radio(
    "Orlando ↔ Seattle round trip",
    ["Option 1 — Delta", "Option 2 — Southwest"],
    index=0, horizontal=True, key="domestic_round_trip",
)
delta = option == "Option 1 — Delta"
carrier = "Delta" if delta else "Southwest"
cabin = "First Classic" if delta else "Choice Extra"
st.caption(f"{carrier} · {cabin} · {'Nonstop both ways' if delta else 'Via Chicago Midway both ways'}")

hotel_options = ["Option 1 — New City 1 + New City 2", "Option 2 — New City 1 only"]
saved_plans = st.session_state.setdefault("custom_hotel_plans", {}).setdefault(DEFAULT_YEAR, {})
hotel_options.extend(saved_plans)
if "next_hotel_plan" in st.session_state:
    st.session_state.hotel_plan = st.session_state.pop("next_hotel_plan")
hotel_plan = st.radio("Japan hotel plan", hotel_options, index=0, horizontal=True, key="hotel_plan")
two_cities = hotel_plan == hotel_options[0]

# Each leg uses the local clock at its respective airport.
zones = {"MCO": "America/New_York", "MDW": "America/Chicago",
         "SEA": "America/Los_Angeles", "Tokyo": "Asia/Tokyo"}
outbound = [("MCO", "18:20", "SEA", "21:50")] if delta else [
    ("MCO", "07:00", "MDW", "08:55"), ("MDW", "10:25", "SEA", "13:00")]
inbound = [("SEA", "08:37", "MCO", "17:04")] if delta else [
    ("SEA", "06:35", "MDW", "12:25"), ("MDW", "13:25", "MCO", "17:00")]

def local_time(stamp, airport):
    return pd.Timestamp(stamp).tz_localize(zones[airport])

def duration(start, end):
    hours, minutes = divmod(int((end - start).total_seconds() // 60), 60)
    return f"{hours}h {minutes:02d}m"

calendar_flights = {}
flights = []
events = []
bars = []
def add_segment(label, start, end, category):
    time_format = "%b %d" if category.endswith("stay") else "%b %d · %I:%M %p %Z"
    bars.append({
        "Segment": label, "Category": category,
        "Start": start.tz_convert("UTC").tz_localize(None),
        "End": end.tz_convert("UTC").tz_localize(None),
        "Local start": start.strftime(time_format), "Local end": end.strftime(time_format),
    })

def flight(label, airline, origin, start, destination, end, order):
    # Sort by travel sequence even when a flight crosses the date line.
    for sequence, stamp, action, airport in [
        (order, start, "Depart", origin), (order + 1, end, "Arrive", destination)
    ]:
        calendar_flights.setdefault(stamp.date(), []).append((sequence, {
            "text": f"✈ {action} {airport}",
            "subtext": f"{stamp:%I:%M %p %Z} · {airline}",
            "color": "flight",
        }))
    flights.append({"Journey": label, "Carrier / cabin": airline, "From": origin,
                    "Departs (local)": start.strftime("%b %d · %I:%M %p"), "To": destination,
                    "Arrives (local)": end.strftime("%b %d · %I:%M %p"), "Elapsed": duration(start, end)})
    events.extend([(start.date(), order, start.strftime("%I:%M %p %Z"), f"Depart {origin} for {destination} · {airline}"),
                   (end.date(), order + 1, end.strftime("%I:%M %p %Z"), f"Arrive in {destination}")])
    add_segment(f"{label} · {origin} → {destination}", start, end,
                "JAL Business" if "Tokyo" in (origin, destination) else carrier)

for direction, prefix, day, legs, order in [
    ("Outbound", "Connecting Outgoing", 3, outbound, 10),
    ("Return", "Connecting Incoming", 17, inbound, 130),
]:
    previous = None
    for i, (origin, dep, destination, arr) in enumerate(legs):
        start = local_time(f"{DEFAULT_YEAR}-02-{day:02d} {dep}", origin)
        end = local_time(f"{DEFAULT_YEAR}-02-{day:02d} {arr}", destination)
        if previous is None:
            first = start
            df[prefix + " Departure Date"] = start.tz_localize(None)
        else:
            label = f"{direction} layover · MDW · {duration(previous, start)}"
            add_segment(label, previous, start, "Layover")
            events.append((previous.date(), order + 2, "MDW", label))
        flight(direction, f"{carrier} {cabin}", origin, start, destination, end, order + 3*i)
        previous = end
    df[prefix + " Arrival Date"] = end.tz_localize(None)
    df[direction + " connector elapsed"] = duration(first, end)

df["Domestic round trip"] = option + " · " + cabin
if delta:
    # These spreadsheet amounts include the Southwest connector.
    df = df.drop(columns=[
        "Connecting Flight Price", "Flight Price", "Per Person Flight",
        "70/30 Split Daniel Flight", "70/30 Split Kelsey Flight", "$ of Highest Savings",
        "Percent of Highest Savings", "Hotel + Flight", "Per Person Total",
        "70/30 Split Daniel Total", "70/30 Split Kelsey Total",
    ], errors="ignore")

row = df.iloc[0]
for label, prefix, origin, destination, order in [
    ("Japan outbound", "Outgoing", "SEA", "Tokyo", 50),
    ("Japan return", "Incoming", "Tokyo", "SEA", 90),
]:
    start, end = row.get(prefix + " Departure Date"), row.get(prefix + " Arrival Date")
    if pd.notna(start) and pd.notna(end):
        flight(label, "JAL Business Class", origin, local_time(start, origin),
               destination, local_time(end, destination), order)

for prefix, label, city, order in [
    ("Connecting Outgoing Hotel", "Seattle outbound hotel", "SEA", 30),
    ("Hotel", "Japan hotel stay", "Tokyo", 70),
    ("Connecting Incoming Hotel", "Seattle return hotel", "SEA", 110),
]:
    start, end = row.get(prefix + " Check In"), row.get(prefix + " Check Out")
    if pd.notna(start) and pd.notna(end):
        add_segment(label, local_time(start, city), local_time(end, city),
                    "Japan stay" if city == "Tokyo" else "Seattle stay")
    if city == "SEA":
        for stamp, action, priority in [(start, "Check in", order), (end, "Check out", order + 1)]:
            if pd.notna(stamp):
                events.append((stamp.date(), priority, action, label))

itinerary, flight_tab, costs = st.tabs(["Itinerary", "Flights", "Costs"])
with flight_tab:
    st.subheader("Trip timeline")
    st.caption("Orlando → Seattle → Tokyo and back · Hover over a segment for local dates and times.")
    colors = {carrier: "#3B82D0", "JAL Business": "#8962C0", "Layover": "#C87A32",
              "Seattle stay": "#C59B43", "Japan stay": "#29936E"}
    timeline = pd.DataFrame(bars).sort_values("Start", kind="stable")
    fig = px.timeline(
        timeline, x_start="Start", x_end="End", y="Segment", color="Category",
        color_discrete_map=colors,
        category_orders={"Segment": timeline["Segment"].tolist(), "Category": list(colors)},
        custom_data=["Segment", "Category", "Local start", "Local end"],
    )
    fig.update_traces(
        width=0.58,
        hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<br>"
                      "%{customdata[2]} → %{customdata[3]}<extra></extra>",
    )
    fig.update_layout(
        height=220 + 33 * len(timeline), xaxis_title="Trip dates (UTC)", yaxis_title="",
        legend=dict(title_text="", orientation="h", yanchor="bottom", y=1.04),
        margin=dict(l=6, r=12, t=68, b=38), bargap=0.32,
    )
    fig.update_xaxes(tickformat="%b %d", nticks=8, showgrid=True)
    fig.update_yaxes(automargin=True)
    st.plotly_chart(fig, use_container_width=True)
    st.subheader("Flight schedule")
    st.caption(f"Orlando → Seattle · {row['Outbound connector elapsed']} total   |   Seattle → Orlando · {row['Return connector elapsed']} total")
    if not delta:
        st.caption("Chicago Midway layovers · 1h 30m outbound · 1h 00m return")
    table = pd.DataFrame(flights)
    order = ["Outbound", "Japan outbound", "Japan return", "Return"]
    table["Journey"] = pd.Categorical(table["Journey"], categories=order, ordered=True)
    st.dataframe(table.sort_values("Journey", kind="stable"), hide_index=True, use_container_width=True)

if delta:
    with costs:
        st.metric("JAL Business Class · discounted round trip for two",
                  fmt_money(row.get("Direct Flight Price (Discounted)")))
else:
    with costs:
        st.caption(f"Southwest domestic round trip for two · {fmt_money(row.get('Connecting Flight Price'))} · prior spreadsheet amount")
        st.markdown("## 🧾 Selected Trip")
    
        row = df.iloc[0]
        airline = row["Airline"]
        tier = row["Travel Tier"]
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
        "End": datetime(DEFAULT_YEAR, 2, 10 if two_cities else 13, 15, 0),
        "Price": None,
        "Label": "New City 1 Hotel",
        "Subtext": "Placeholder • 2 nights" if two_cities else "Placeholder • 5 nights",
        "Emoji": "🏙️",
        "Color": "city1",
    },
]
if two_cities:
    calendar_items.append({
        "Name": "New City 2 Hotel",
        "Type": "Hotel Placeholder",
        "Start": datetime(DEFAULT_YEAR, 2, 10, 11, 0),
        "End": datetime(DEFAULT_YEAR, 2, 13, 15, 0),
        "Price": None,
        "Label": "New City 2 Hotel",
        "Subtext": "Placeholder • 3 nights",
        "Emoji": "🌆",
        "Color": "city2",
    })
calendar_items.append({
        "Name": "Hilton",
        "Type": "Hotel",
        "Start": datetime(DEFAULT_YEAR, 2, 13, 11, 0),
        "End": datetime(DEFAULT_YEAR, 2, 16, 15, 0),
        "Price": 982.84,
        "Label": "Hilton stay",
        "Subtext": "$982.84 total",
        "Emoji": "🏨",
        "Color": "hilton2",
    })

def propose_edit(api_key, context):
    def obj(properties):
        return {"type": "object", "properties": properties, "required": list(properties),
                "additionalProperties": False}

    string = {"type": "string"}
    change = obj({
        "action": {"type": "string", "enum": ["update_stay", "add_stay", "remove_stay",
                                              "update_activity", "add_activity", "remove_activity"]},
        "id": string, "name": string, "start": string, "end": string,
        "price_mode": {"type": "string", "enum": ["keep", "total", "nightly", "clear"]},
        "amount": {"type": ["number", "null"]},
    })
    schema = obj({"question": string, "changes": {"type": "array", "items": change}})
    rules = """Edit the displayed Japan plan using the request and any prior clarification.
Return a minimal set of changes or one specific question with no changes. Preserve unrelated facts.
Resolve names, ordinals, weekdays and relative dates against the supplied calendar. Check ALL clues:
if City 1 does not end on the stated Saturday but City 2 does, ask which the user means.
Two Hilton stays are distinct. 'Accordingly' means move the adjoining checkout and check-in together.
For a clear boundary edit return two update_stay entries. If a freed night has two plausible destinations,
ask. For splitting/merging or adding a city, update/add/remove stays together so every night is covered.
First arrival and last departure are fixed; flights are read-only. For unsupported requests explain briefly.
Use existing IDs for update/remove, empty id for add. Fields with no requested change are empty strings.
Dates are ISO YYYY-MM-DD. An activity uses start for its date, end empty. Activities can be renamed or moved.
Prices are USD. price_mode keep (amount null) preserves quoted totals on date changes; clear means unknown.
For explicitly nightly prices use nightly; Python multiplies by nights. Do not invent prices or activities.
When a split/merge leaves allocation of existing known costs unclear, ask. No bookings. Reply using the schema."""
    payload = {"model": "gpt-5.4-mini", "messages": [
        {"role": "system", "content": rules},
        {"role": "user", "content": json.dumps(context)}],
        "response_format": {"type": "json_schema", "json_schema": {
            "name": "itinerary_edit", "strict": True, "schema": schema}}}
    req = Request("https://api.openai.com/v1/chat/completions",
                  data=json.dumps(payload).encode(), headers={"Content-Type": "application/json",
                  "Authorization": "Bearer " + api_key})
    with urlopen(req, timeout=45) as response:
        message = json.load(response)["choices"][0]["message"]
    if not message.get("content"):
        raise ValueError("No proposed edit was returned. Please rephrase the request.")
    return json.loads(message["content"])


def apply_changes(plan, changes):
    """Apply the entire proposal to a temporary copy and validate the resulting calendar."""
    draft = deepcopy(plan)
    original_start = plan["stays"][0]["Start"].date()
    original_end = plan["stays"][-1]["End"].date()
    if not changes or len(changes) > 60:
        raise ValueError("Which stay or activity would you like to change?")
    for edit in changes:
        verb, kind = edit["action"].split("_", 1)
        if kind not in ("activity", "stay") or verb not in ("add", "update", "remove"):
            raise ValueError("Choose a hotel stay or day activity to edit.")
        rows = draft["stays" if kind == "stay" else "activities"]
        name = edit["name"].strip()
        if len(name) > 160 or (verb == "add" and not name):
            raise ValueError("What short name should this entry have?")
        if verb == "add":
            item = {"id": uuid4().hex}
            if kind == "stay":
                item.update(Type="Hotel", Emoji="🏨", Color="city1", Price=None)
            rows.append(item)
        else:
            item = next((r for r in rows if r["id"] == edit["id"]), None)
            if item is None:
                raise ValueError("Which entry on the displayed calendar did you mean? Please give its name and date.")
            if verb == "remove":
                rows.remove(item)
                continue
        if kind == "activity":
            if name:
                item["name"] = name
            if edit["start"]:
                item["date"] = date.fromisoformat(edit["start"]).isoformat()
            if not original_start.isoformat() <= item.get("date", "") <= original_end.isoformat():
                raise ValueError("Which day during the Japan stay should this activity use?")
            continue
        if name:
            item["Name"] = item["Label"] = name
        for field, key, hour in [("start", "Start", 11), ("end", "End", 15)]:
            if edit[field]:
                clock = item[key].time() if key in item else datetime.min.replace(hour=hour).time()
                item[key] = datetime.combine(date.fromisoformat(edit[field]), clock)
        if "Start" not in item or "End" not in item:
            raise ValueError("What are the check-in and checkout dates for the new stay?")
        nights = (item["End"].date() - item["Start"].date()).days
        mode, amount = edit["price_mode"], edit["amount"]
        if mode in ("nightly", "total"):
            if type(amount) not in (int, float) or not math.isfinite(amount) or amount < 0:
                raise ValueError("What nonnegative USD price should this stay use?")
            item["Price"] = round(amount * (nights if mode == "nightly" else 1), 2)
        elif mode == "clear":
            item["Price"] = None
        elif mode != "keep" or amount is not None:
            raise ValueError("Is that price per night or for the whole stay?")
    stays = draft["stays"]
    stays.sort(key=lambda s: s["Start"])
    if not stays or stays[0]["Start"].date() != original_start or stays[-1]["End"].date() != original_end:
        raise ValueError(f"Which hotel covers the endpoints of the Japan stay ({original_start} to {original_end})?")
    for i, stay in enumerate(stays):
        if stay["End"].date() <= stay["Start"].date():
            raise ValueError(f"{stay['Name']} needs at least one night. Should that stay be removed?")
        if i and stays[i-1]["End"].date() != stay["Start"].date():
            raise ValueError(f"Which date should be the transfer from {stays[i-1]['Name']} to {stay['Name']}?")
    if draft == plan:
        raise ValueError("The calendar already matches that change. What would you like to adjust?")
    return draft


for index, stay in enumerate(calendar_items):
    stay["id"] = f"stay-{index + 1}"
baseline = saved_plans.get(hotel_plan, {"stays": calendar_items, "activities": []})
drafts = st.session_state.setdefault("trip_drafts", {})
scope = (DEFAULT_YEAR, hotel_plan)
work = drafts.setdefault(scope, {"draft": None, "conversation": []})
view_key = f"plan_view_{DEFAULT_YEAR}_{hotel_plan}"

with itinerary:
    with st.expander("Edit this trip with AI"):
        st.caption("Edit hotel dates, stay prices, or day activities. Saved options last for this session.")
        current = work["draft"] if work["draft"] and st.session_state.get(view_key, "Draft") == "Draft" else baseline
        if work.get("pending_source") != current:
            work["conversation"] = []
        if work["conversation"]:
            st.info(work["conversation"][-1]["question"])
        with st.form(f"edit_{view_key}", clear_on_submit=True):
            prompt = st.text_area("What would you change?", placeholder="Move the City 1 → City 2 transfer to February 9.")
            submitted = st.form_submit_button("Update draft")
        if submitted and prompt.strip():
            work["pending_source"] = current
            try:
                key = os.environ.get("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
            except FileNotFoundError:
                key = None
            if not key:
                st.error("Add OPENAI_API_KEY to Streamlit secrets to enable the editor.")
            else:
                context = {"stays": [{"id": x["id"], "hotel": x["Name"], "check_in": x["Start"].date().isoformat(),
                            "check_out": x["End"].date().isoformat(), "check_in_weekday": x["Start"].strftime("%A"), "check_out_weekday": x["End"].strftime("%A"), "total_usd": x["Price"]} for x in current["stays"]],
                           "activities": current["activities"], "hotel_option": hotel_plan, "flights": flights,
                           "clarifications": work["conversation"], "request": prompt}
                try:
                    with st.spinner("Updating draft…"):
                        reply = propose_edit(key, context)
                    if reply["question"]:
                        work["conversation"].append({"request": prompt, "question": reply["question"]})
                        st.info(reply["question"])
                    else:
                        work["draft"] = apply_changes(current, reply["changes"])
                        work["conversation"] = []
                        st.session_state[view_key] = "Draft"
                        st.success("Draft updated.")
                except HTTPError as error:
                    try:
                        detail = json.loads(error.read()).get("error", {})
                        reason = detail.get("code") or detail.get("type") or "unknown"
                    except (ValueError, AttributeError):
                        reason = "unknown"
                    st.error(f"OpenAI HTTP {error.code} · {reason}")
                except (ValueError, KeyError, TypeError, IndexError, OSError) as error:
                    if isinstance(error, ValueError):
                        question = str(error)
                        work["conversation"].append({"request": prompt, "question": question})
                        st.info(question)
                    else:
                        st.error("The response could not be processed. Please try again.")
        if work["draft"] is not None:
            st.caption("Draft hotel stays")
            st.dataframe(pd.DataFrame([{
                "Hotel": h["Name"], "Check-in": h["Start"].date(),
                "Checkout": h["End"].date(), "Total": fmt_money(h["Price"]),
            } for h in work["draft"]["stays"]]), hide_index=True, use_container_width=True)
            if st.button("Save as Option " + str(3 + len(saved_plans)), key="save_" + view_key):
                label = f"Option {3 + len(saved_plans)} — Custom plan"
                saved_plans[label] = deepcopy(work["draft"])
                st.session_state["next_hotel_plan"] = label
                st.rerun()
        if work["draft"] is not None or work["conversation"]:
            if st.button("Discard draft", key="discard_" + view_key):
                drafts.pop(scope)
                st.session_state.pop(view_key, None)
                st.rerun()
    showing_draft = work["draft"] is not None and st.radio(
        "Calendar version", ["Original", "Draft"], horizontal=True, key=view_key) == "Draft"
active = work["draft"] if showing_draft else baseline
calendar_items = active["stays"]
activities = active["activities"]

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


with costs:
    st.metric("Known Japan hotel cost · active calendar", fmt_money(total_known_hotel_cost))
    st.caption("Spreadsheet package figures use the original hotel budget.")

with itinerary:
    st.subheader("Trip calendar & day-by-day plan")
    days = [e[0] for e in events] + [d.date() for d in calendar_df["End"]]
    selected_date = st.date_input("Trip date", value=min(days), min_value=min(days), max_value=max(days))
    left, right = st.columns([1.15, 1])
    with right:
        st.subheader("Day-by-day plan")
        mode = st.radio("View", ["Selected day", "Full trip"], horizontal=True)
        dates = [selected_date] if mode == "Selected day" else pd.date_range(min(days), max(days)).date
        for day in dates:
            st.markdown(f"**{day:%A, %B %d}**")
            for _, priority, clock, title in sorted(e for e in events if e[0] == day):
                st.write(f"{clock} · {title}")
            for hotel in calendar_items:
                start, end = hotel["Start"].date(), hotel["End"].date()
                if start <= day <= end:
                    status = "Check in" if day == start else "Check out" if day == end else "Stay night"
                    st.write(f"{status} · {hotel['Name']}")
            for activity in activities:
                if activity["date"] == day.isoformat():
                    st.text(activity["name"])
            if mode == "Full trip":
                st.divider()
    with left:
        st.subheader("Trip calendar")
        st.caption(f"February {DEFAULT_YEAR} · {total_known_hotel_nights} priced nights · {fmt_money(total_known_hotel_cost)} known hotel cost")
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

            for activity in activities:
                if activity["date"] == day_date.isoformat():
                    events.append({"text": activity["name"], "subtext": "Day activity", "color": "flight"})
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
            .hotel-pill.flight {
                background: #334155;
                border-left: 3px solid #fbbf24;
                overflow-wrap: anywhere;
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
            <div class="hotel-chip">✈ Flights · local times</div>
            <div class="hotel-chip">🏨 Hotel stays</div>
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
                outline = "box-shadow: inset 0 0 0 2px #168576" if day == selected_date else ""
                calendar_html += f'<div class="hotel-day{muted_class}" style="{outline}">'
                calendar_html += f'<div class="hotel-day-number">{day.day}</div>'

                if day.month == 2:
                    flight_items = [item for _, item in sorted(calendar_flights.get(day, []))]
                    for event in item_events_for_day(day) + flight_items:
                        calendar_html += f"""
                        <div class="hotel-pill {event['color']}">
                            <div class="hotel-pill-main">{escape(event['text'])}</div>
                            <div class="hotel-pill-sub">{escape(event['subtext'])}</div>
                        </div>
                        """

                calendar_html += '</div>'

        calendar_html += '</div></div>'

        components.html(calendar_html, height=820, scrolling=True)

        # --------------------------------------------------

    with st.expander("Stay details and hotel notes"):


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

        if not showing_draft and hotel_plan not in saved_plans:
            st.markdown("### Hotel Flow Notes")

            note_cols = st.columns(3)

            with note_cols[0]:
                st.markdown(
                    f"""
                    **2/13 — Hilton check-in**  
                    Move from {"New City 2" if two_cities else "New City 1"} back to Hilton, bag drop/check in, then keep the evening flexible.
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



with st.expander("View cleaned trip data"):
    st.dataframe(df, use_container_width=True)
