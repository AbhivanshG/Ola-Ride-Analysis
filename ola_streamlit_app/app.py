"""
Ola Ride Analytics - a simple Streamlit dashboard.

How this file is organised (top to bottom):
  1. Settings        - colours, vehicle names, file paths
  2. Data cleaning   - load the CSV and fill the blanks
  3. Small helpers   - number formatting, charts, vehicle cards
  4. Pages           - one function per page of the dashboard
  5. Main            - sidebar navigation + date filter, then show the chosen page
"""

import base64
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# ----------------------------------------------------------------------------
# 1. SETTINGS
# ----------------------------------------------------------------------------
st.set_page_config(page_title="Ola Ride Analytics", page_icon="🚖", layout="wide")

BASE = Path(__file__).parent
DATA_FILE = BASE / "data" / "cleaned_eda_data.csv"
ASSETS = BASE / "assets"

GREEN = "#6BBF3B"
DARK = "#262626"

VEHICLES = ["Prime Sedan", "Prime SUV", "Prime Plus", "Mini", "Auto", "Bike", "eBike"]
ICON_FILES = {
    "Prime Sedan": "prime_sedan.png",
    "Prime SUV": "prime_suv.png",
    "Prime Plus": "prime_plus.png",
    "Mini": "mini.png",
    "Auto": "auto.png",
    "Bike": "bike.png",
    "eBike": "ebike.png",
}
SHOW_NAME = {"eBike": "E-Bike"}  # how a vehicle is written on screen

STATUS_COLORS = {
    "Success": GREEN,
    "Canceled by Customer": "#F5A623",
    "Canceled by Driver": "#E5533D",
    "Driver Not Found": "#7F8C8D",
}

# Values that mean "this cell has no real data"
MISSING_TEXT = ["No Data", "", " "]
# Number columns with blanks -> filled with the MEDIAN
NUMBER_COLS = ["V TAT", "C TAT", "Driver Ratings", "Customer Rating"]
# Text columns with "No Data" -> filled with "Not Applicable"
TEXT_COLS = [
    "Canceled Rides by Customer",
    "Canceled Rides by Driver",
    "Incomplete Rides",
    "Incomplete Rides Reason",
    "Payment Method",
]


# ----------------------------------------------------------------------------
# 2. DATA CLEANING
# ----------------------------------------------------------------------------
def count_missing(frame: pd.DataFrame) -> pd.Series:
    """Count blank cells and 'No Data' cells in every column."""
    return (frame.isna() | frame.isin(MISSING_TEXT)).sum()


@st.cache_data(show_spinner="Loading and cleaning the data...")
def prepare(raw: pd.DataFrame):
    """Fill all the blanks and return (clean data, a report of what was changed)."""
    before = count_missing(raw)
    df = raw.copy()

    # Step 1: drop columns that are 100% empty (nothing to learn from them)
    empty_cols = [c for c in df.columns if before[c] == len(df)]
    df = df.drop(columns=empty_cols)

    # Step 2: make dates and hours usable
    df["Date"] = pd.to_datetime(df["Date"])
    df["Day"] = df["Date"].dt.normalize()
    df["Hour"] = pd.to_datetime(df["Time"], format="%H:%M:%S", errors="coerce").dt.hour

    # Step 3: turn "No Data" into real blanks in the number columns
    for col in NUMBER_COLS:
        df[col] = pd.to_numeric(df[col].replace("No Data", np.nan), errors="coerce")

    # Remember which rows we are about to fill (so we can always tell them apart)
    df["Was Filled"] = df[NUMBER_COLS].isna().any(axis=1)

    # Step 4: fill number blanks with the MEDIAN of each vehicle type.
    # The median is calculated only from successful rides (real data).
    success = df["Booking Status"] == "Success"
    medians = df[success].groupby("Vehicle Type")[NUMBER_COLS].median()
    for col in NUMBER_COLS:
        df[col] = df[col].fillna(df["Vehicle Type"].map(medians[col]))

    # Step 5: fill text blanks with "Not Applicable"
    for col in TEXT_COLS:
        df[col] = df[col].replace(MISSING_TEXT, "Not Applicable")

    # Build a small report for the "Data & Cleaning" page
    how = {c: "Median of the same vehicle type (successful rides)" for c in NUMBER_COLS}
    how.update({c: 'Filled with "Not Applicable"' for c in TEXT_COLS})
    how.update({c: "Column removed (completely empty)" for c in empty_cols})
    after = count_missing(df)
    rows = []
    for col in raw.columns:
        if before[col] > 0:
            rows.append(
                {
                    "Column": col,
                    "Blank cells before": int(before[col]),
                    "How it was handled": how.get(col, ""),
                    "Blank cells after": int(after[col]) if col in df.columns else 0,
                }
            )
    return df, pd.DataFrame(rows)


@st.cache_data
def to_csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False).encode("utf-8")


# ----------------------------------------------------------------------------
# 3. SMALL HELPERS
# ----------------------------------------------------------------------------
def money(x: float) -> str:
    return f"₹{x / 1e6:.2f}M" if abs(x) >= 1e6 else f"₹{x:,.0f}"


def whole(x: float) -> str:
    return f"{x:,.0f}"


def nice(vehicle: str) -> str:
    return SHOW_NAME.get(vehicle, vehicle)


@st.cache_resource
def icon_uri(vehicle: str) -> str:
    """Turn a vehicle picture into text so it can sit inside a table."""
    data = (ASSETS / ICON_FILES[vehicle]).read_bytes()
    return "data:image/png;base64," + base64.b64encode(data).decode()


def style(fig, height=360):
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=50, b=10),
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend_title_text="",
    )
    return fig


def show(fig):
    st.plotly_chart(fig, width="stretch")


def vehicle_cards(values: dict, fmt):
    """One small card per vehicle type: picture, name and a value."""
    columns = st.columns(len(VEHICLES))
    for col, vehicle in zip(columns, VEHICLES):
        with col, st.container(border=True):
            st.image(str(ASSETS / ICON_FILES[vehicle]), width=56)
            st.caption(nice(vehicle))
            st.markdown(f"**{fmt(values.get(vehicle, 0))}**")


def insight(text: str):
    st.info("💡 **What this tells us:** " + text)


def hbar(series: pd.Series, title: str, color=GREEN):
    """Horizontal bar chart from a Series (biggest bar on top)."""
    fig = px.bar(x=series.values, y=series.index, orientation="h", title=title)
    fig.update_traces(marker_color=color)
    fig.update_yaxes(autorange="reversed", title="")
    fig.update_xaxes(title="")
    return style(fig)


# ----------------------------------------------------------------------------
# 4. PAGES
# ----------------------------------------------------------------------------
def page_overall(df, ok):
    st.title("📊 Overall Summary")
    st.caption("A quick snapshot of every Ola booking in the dates you selected.")

    total, wins = len(df), len(ok)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Bookings", whole(total))
    c2.metric("Successful Rides", whole(wins))
    c3.metric("Success Rate", f"{wins / total * 100:.1f}%")
    c4.metric("Total Revenue", money(ok["Booking Value"].sum()))
    c5.metric("Distance Travelled", f"{ok['Ride Distance'].sum() / 1e6:.2f}M km")

    left, right = st.columns([3, 2])
    daily = df.groupby(["Day", "Booking Status"]).size().reset_index(name="Bookings")
    fig = px.line(
        daily, x="Day", y="Bookings", color="Booking Status",
        color_discrete_map=STATUS_COLORS, title="Bookings per day",
    )
    fig.update_xaxes(title="")
    with left:
        show(style(fig))
    status = df["Booking Status"].value_counts().reset_index()
    status.columns = ["Booking Status", "Bookings"]
    fig = px.pie(
        status, names="Booking Status", values="Bookings", hole=0.55,
        color="Booking Status", color_discrete_map=STATUS_COLORS,
        title="What happened to the bookings?",
    )
    with right:
        show(style(fig))

    left, right = st.columns(2)
    hourly = ok.groupby("Hour").size().reset_index(name="Rides")
    fig = px.bar(hourly, x="Hour", y="Rides", title="Successful rides by hour of the day")
    fig.update_traces(marker_color=GREEN)
    fig.update_xaxes(dtick=2)
    with left:
        show(style(fig))
    top_pickup = ok["Pickup Location"].value_counts().head(5)
    with right:
        show(hbar(top_pickup, "Top 5 pickup locations"))

    busiest = daily.groupby("Day")["Bookings"].sum().idxmax()
    peak_hour = hourly.loc[hourly["Rides"].idxmax(), "Hour"]
    insight(
        f"Out of {whole(total)} bookings, {wins / total * 100:.0f}% were completed. "
        f"The busiest day was {busiest:%d %b %Y}, the busiest hour of the day is "
        f"{int(peak_hour)}:00, and {top_pickup.index[0]} is the most popular pickup area."
    )


def page_vehicle(df, ok):
    st.title("🚗 Vehicle Type")
    st.caption("How each type of vehicle performs: bookings, money and distance.")

    everything = df.groupby("Vehicle Type")["Booking Value"].sum().rename("Total Booking Value (₹)")
    wins = ok.groupby("Vehicle Type").agg(
        **{
            "Success Booking Value (₹)": ("Booking Value", "sum"),
            "Avg. Distance (km)": ("Ride Distance", "mean"),
            "Total Distance (km)": ("Ride Distance", "sum"),
            "Successful Rides": ("Booking ID", "count"),
            "Avg V TAT": ("V TAT", "mean"),
            "Avg C TAT": ("C TAT", "mean"),
        }
    )
    table = pd.concat([everything, wins], axis=1).reindex(VEHICLES)

    show_table = table[
        ["Total Booking Value (₹)", "Success Booking Value (₹)", "Avg. Distance (km)", "Total Distance (km)"]
    ].copy()
    show_table.insert(0, "Vehicle", [nice(v) for v in show_table.index])
    show_table.insert(0, "Icon", [icon_uri(v) for v in show_table.index])
    st.dataframe(
        show_table,
        hide_index=True,
        width="stretch",
        row_height=48,
        column_config={
            "Icon": st.column_config.ImageColumn("", width="small"),
            "Total Booking Value (₹)": st.column_config.NumberColumn(format="%d"),
            "Success Booking Value (₹)": st.column_config.NumberColumn(format="%d"),
            "Avg. Distance (km)": st.column_config.NumberColumn(format="%.1f"),
            "Total Distance (km)": st.column_config.NumberColumn(format="%d"),
        },
    )
    st.caption(
        "Total Booking Value counts every booking (even cancelled ones). "
        "Success Booking Value counts only completed rides."
    )

    left, right = st.columns(2)
    d = table.reset_index().rename(columns={"index": "Vehicle Type"})
    d["Vehicle"] = d["Vehicle Type"].map(nice)
    fig = px.bar(d.sort_values("Successful Rides"), x="Successful Rides", y="Vehicle",
                 orientation="h", title="Successful rides")
    fig.update_traces(marker_color=GREEN)
    fig.update_yaxes(title="")
    with left:
        show(style(fig))
    fig = px.bar(d.sort_values("Avg. Distance (km)"), x="Avg. Distance (km)", y="Vehicle",
                 orientation="h", title="Average distance per ride (km)")
    fig.update_traces(marker_color=DARK)
    fig.update_yaxes(title="")
    with right:
        show(style(fig))

    tat = d.melt(id_vars="Vehicle", value_vars=["Avg V TAT", "Avg C TAT"],
                 var_name="Measure", value_name="Average")
    fig = px.bar(tat, x="Vehicle", y="Average", color="Measure", barmode="group",
                 color_discrete_sequence=[GREEN, DARK], title="Average V TAT and C TAT")
    fig.update_xaxes(title="")
    show(style(fig, 320))
    st.caption("TAT = turnaround time. V TAT is for the vehicle, C TAT is for the customer. Lower is quicker.")

    best = table["Successful Rides"].idxmax()
    far = table["Avg. Distance (km)"].idxmax()
    short = table["Avg. Distance (km)"].idxmin()
    insight(
        f"{nice(best)} has the most completed rides ({whole(table.loc[best, 'Successful Rides'])}). "
        f"{nice(far)} rides are the longest on average ({table.loc[far, 'Avg. Distance (km)']:.1f} km), "
        f"while {nice(short)} is used for the shortest trips ({table.loc[short, 'Avg. Distance (km)']:.1f} km)."
    )


def page_revenue(df, ok):
    st.title("₹ Revenue")
    st.caption("How much money the rides bring in, and how much is lost to cancellations.")

    revenue = ok["Booking Value"].sum()
    lost = df.loc[df["Booking Status"] != "Success", "Booking Value"].sum()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Revenue", money(revenue))
    c2.metric("Average Booking Value", money(ok["Booking Value"].mean()))
    c3.metric("Revenue per km", f"₹{revenue / ok['Ride Distance'].sum():.1f}")
    c4.metric("Lost to Cancellations", money(lost))

    left, right = st.columns(2)
    daily = ok.groupby("Day")["Booking Value"].sum().reset_index()
    fig = px.line(daily, x="Day", y="Booking Value", title="Revenue per day (₹)")
    fig.update_traces(line_color=GREEN)
    fig.update_xaxes(title="")
    with left:
        show(style(fig))
    pay = ok.groupby("Payment Method")["Booking Value"].sum().reset_index()
    fig = px.pie(pay, names="Payment Method", values="Booking Value", hole=0.55,
                 title="Revenue by payment method",
                 color_discrete_sequence=[GREEN, DARK, "#A5D86E", "#8C8C8C", "#C9E7A8"])
    with right:
        show(style(fig))

    left, right = st.columns(2)
    by_vehicle = ok.groupby("Vehicle Type")["Booking Value"].sum().reindex(VEHICLES)
    by_vehicle.index = [nice(v) for v in by_vehicle.index]
    with left:
        show(hbar(by_vehicle.sort_values(ascending=False), "Revenue by vehicle type (₹)"))
    by_status = df.groupby("Booking Status")["Booking Value"].sum().reset_index()
    fig = px.bar(by_status, x="Booking Status", y="Booking Value", color="Booking Status",
                 color_discrete_map=STATUS_COLORS, title="Booking value by outcome (₹)")
    fig.update_layout(showlegend=False)
    fig.update_xaxes(title="")
    with right:
        show(style(fig))

    st.subheader("Average booking value per vehicle")
    avg = ok.groupby("Vehicle Type")["Booking Value"].mean().to_dict()
    vehicle_cards(avg, lambda v: f"₹{v:,.0f}")

    top_pay = pay.loc[pay["Booking Value"].idxmax(), "Payment Method"]
    top_vehicle = by_vehicle.idxmax()
    insight(
        f"Completed rides earned {money(revenue)}. {top_vehicle} brings in the most money, "
        f"and {top_pay} is the payment method that earns the most. "
        f"Cancelled or unfilled bookings represent about {money(lost)} of rides that did not happen."
    )


def page_cancellation(df, ok):
    st.title("❌ Cancellation")
    st.caption("Which rides did not happen, who cancelled, and why.")

    status = df["Booking Status"].value_counts()
    not_done = df[df["Booking Status"] != "Success"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cancelled by Customer", whole(status.get("Canceled by Customer", 0)))
    c2.metric("Cancelled by Driver", whole(status.get("Canceled by Driver", 0)))
    c3.metric("Driver Not Found", whole(status.get("Driver Not Found", 0)))
    c4.metric("Overall Cancellation Rate", f"{len(not_done) / len(df) * 100:.1f}%")

    left, right = st.columns(2)
    cust = df.loc[df["Canceled Rides by Customer"] != "Not Applicable", "Canceled Rides by Customer"]
    drv = df.loc[df["Canceled Rides by Driver"] != "Not Applicable", "Canceled Rides by Driver"]
    with left:
        show(hbar(cust.value_counts(), "Why customers cancel", "#F5A623"))
    with right:
        show(hbar(drv.value_counts(), "Why drivers cancel", "#E5533D"))

    st.subheader("Cancelled or unfilled bookings per vehicle")
    per_vehicle = not_done["Vehicle Type"].value_counts().to_dict()
    vehicle_cards(per_vehicle, whole)

    left, right = st.columns(2)
    rate = (df["Booking Status"] != "Success").groupby(df["Vehicle Type"]).mean().mul(100).reindex(VEHICLES)
    rate.index = [nice(v) for v in rate.index]
    with left:
        show(hbar(rate.sort_values(ascending=False).round(1), "Cancellation rate by vehicle (%)", DARK))
    incomplete = ok.loc[ok["Incomplete Rides"] == "Yes", "Incomplete Rides Reason"]
    with right:
        show(hbar(incomplete.value_counts(), "Why completed rides were marked incomplete"))

    top_c = cust.value_counts().idxmax()
    top_d = drv.value_counts().idxmax()
    worst = rate.idxmax()
    insight(
        f"{len(not_done) / len(df) * 100:.0f}% of bookings did not end in a ride. "
        f'The top reason customers cancel is "{top_c}", and for drivers it is "{top_d}". '
        f"{worst} has the highest cancellation rate ({rate.max():.1f}%)."
    )


def page_ratings(df, ok):
    st.title("⭐ Ratings")
    st.caption("How happy are drivers and customers? Only completed rides are rated.")

    c1, c2 = st.columns(2)
    c1.metric("Average Driver Rating", f"{ok['Driver Ratings'].mean():.2f} / 5")
    c2.metric("Average Customer Rating", f"{ok['Customer Rating'].mean():.2f} / 5")

    st.subheader("Driver rating by vehicle")
    drv = ok.groupby("Vehicle Type")["Driver Ratings"].mean().to_dict()
    vehicle_cards(drv, lambda v: f"{v:.2f} ⭐")
    st.subheader("Customer rating by vehicle")
    cus = ok.groupby("Vehicle Type")["Customer Rating"].mean().to_dict()
    vehicle_cards(cus, lambda v: f"{v:.2f} ⭐")

    left, right = st.columns(2)
    fig = px.histogram(ok, x="Driver Ratings", nbins=20, title="How drivers are rated")
    fig.update_traces(marker_color=GREEN)
    fig.update_yaxes(title="Rides")
    with left:
        show(style(fig))
    fig = px.histogram(ok, x="Customer Rating", nbins=20, title="How customers are rated")
    fig.update_traces(marker_color=DARK)
    fig.update_yaxes(title="Rides")
    with right:
        show(style(fig))

    best = max(drv, key=drv.get)
    worst = min(drv, key=drv.get)
    insight(
        f"Drivers average {ok['Driver Ratings'].mean():.2f} and customers {ok['Customer Rating'].mean():.2f} out of 5. "
        f"{nice(best)} drivers score highest ({drv[best]:.2f}) and {nice(worst)} lowest ({drv[worst]:.2f}), "
        "but the gap is tiny, so rating quality is similar across all vehicle types."
    )


def page_cleaning(full, report, raw):
    st.title("🧹 Data & Cleaning")
    st.caption("What was wrong with the data, and exactly how it was fixed.")

    st.markdown(
        """
**Why were there blanks?** Cancelled rides never happened, so they have no rating,
no payment method and no travel time. The blanks are not mistakes, but a dashboard
works best when every cell has a value, so they were filled like this:

- **Number columns (ratings, V TAT, C TAT) → median.** The median is the middle value,
  so a few unusual rides cannot pull it up or down. It is calculated **separately for each
  vehicle type**, using only completed rides.
- **Text columns (payment method, cancel reasons...) → "Not Applicable".** Filling these
  with the most common value (the mode) would be wrong: it would claim that a cancelled ride
  was paid by UPI, or that a ride was cancelled for a reason it never had.
- **Completely empty columns → removed.** *Vehicle Images* had nothing in it.
        """
    )
    st.success(
        "✅ **Every chart in this app uses completed rides only**, and completed rides had no "
        "blanks. So the filled values make the table complete **without changing any result.**"
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Rows", whole(len(full)))
    c2.metric("Rows with filled values", whole(full["Was Filled"].sum()))
    c3.metric("Blank cells left", whole(int(count_missing(full.drop(columns=["Was Filled"])).sum())))

    st.subheader("Blank cells: before and after")
    st.dataframe(report, hide_index=True, width="stretch")

    st.subheader("Preview of the cleaned data")
    st.dataframe(full.drop(columns=["Day", "Hour"]).head(100), hide_index=True, width="stretch")
    st.download_button(
        "⬇️ Download the cleaned data (CSV)",
        data=to_csv_bytes(full.drop(columns=["Day", "Hour"])),
        file_name="ola_cleaned_filled.csv",
        mime="text/csv",
    )


# ----------------------------------------------------------------------------
# 5. MAIN: sidebar, filter, show the chosen page
# ----------------------------------------------------------------------------
def load_raw() -> pd.DataFrame:
    if DATA_FILE.exists():
        return pd.read_csv(DATA_FILE)
    st.warning("The data file was not found in the app folder. Please upload your CSV below.")
    uploaded = st.file_uploader("Upload cleaned_eda_data.csv", type="csv")
    if uploaded is None:
        st.stop()
    return pd.read_csv(uploaded)


def sidebar_logo():
    circle = base64.b64encode((ASSETS / "logo_circle.png").read_bytes()).decode()
    text = base64.b64encode((ASSETS / "logo_text.png").read_bytes()).decode()
    st.sidebar.markdown(
        f"""
        <div style="background:{DARK};border-radius:10px;padding:12px 14px;
                    display:flex;align-items:center;gap:10px;">
            <img src="data:image/png;base64,{circle}" style="height:40px;">
            <img src="data:image/png;base64,{text}" style="height:30px;">
        </div>
        """,
        unsafe_allow_html=True,
    )


PAGES = [
    "📊 Overall",
    "🚗 Vehicle Type",
    "₹ Revenue",
    "❌ Cancellation",
    "⭐ Ratings",
    "🧹 Data & Cleaning",
]


def main():
    raw = load_raw()
    full, report = prepare(raw)

    sidebar_logo()
    st.sidebar.write("")
    page = st.sidebar.radio("Go to page", PAGES)

    st.sidebar.divider()
    first, last = full["Day"].min().date(), full["Day"].max().date()
    picked = st.sidebar.date_input("Date range", value=(first, last), min_value=first, max_value=last)
    st.sidebar.caption("The date range applies to every page except Data & Cleaning.")
    if len(picked) != 2:
        st.sidebar.info("Pick an end date to continue.")
        st.stop()

    df = full[(full["Day"] >= pd.Timestamp(picked[0])) & (full["Day"] <= pd.Timestamp(picked[1]))]
    if df.empty:
        st.warning("No bookings in this date range. Please choose different dates.")
        st.stop()
    ok = df[df["Booking Status"] == "Success"]  # completed rides = real, unfilled data

    if page == PAGES[0]:
        page_overall(df, ok)
    elif page == PAGES[1]:
        page_vehicle(df, ok)
    elif page == PAGES[2]:
        page_revenue(df, ok)
    elif page == PAGES[3]:
        page_cancellation(df, ok)
    elif page == PAGES[4]:
        page_ratings(df, ok)
    else:
        page_cleaning(full, report, raw)


main()
