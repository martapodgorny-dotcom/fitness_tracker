import streamlit as st
import pandas as pd
import os
import re
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from collections import defaultdict

# =============================
# CONFIG
# =============================

RAW_DATA_FOLDER = "Raw_data"
CARDIO_FOLDER = "Cardio_data"
BODY_GROUP_FILE = "body_groups.json"

st.set_page_config(layout="wide")
st.title("🏋️ Fitness Tracker Dashboard")

# =============================
# LOAD BODY GROUPS
# =============================

with open(BODY_GROUP_FILE, "r") as f:
    body_groups = json.load(f)

# =============================
# PARSE DATE FROM FILENAME
# =============================

def parse_date_from_filename(filename):
    match = re.match(r"(\d{6})", filename)
    if not match:
        return None
    date_str = match.group(1)
    return datetime.strptime(date_str, "%d%m%y")

# =============================
# LOAD STRENGTH DATA
# =============================

strength_data = []

for file in os.listdir(RAW_DATA_FOLDER):
    if file.endswith(".txt"):
        filepath = os.path.join(RAW_DATA_FOLDER, file)
        date = parse_date_from_filename(file)

        df = pd.read_csv(filepath, sep="\t")

        df["Weight"] = (
            df["Weight"]
            .astype(str)
            .str.replace(" kg", "", regex=False)
            .str.replace(",", ".", regex=False)
        )

        df["Weight"] = pd.to_numeric(df["Weight"], errors="coerce")

        df["Date"] = date
        strength_data.append(df)

if strength_data:
    strength_df = pd.concat(strength_data, ignore_index=True)
else:
    strength_df = pd.DataFrame()

# =============================
# STRENGTH SUMMARY
# =============================

st.header("📊 Strength Overview")

if not strength_df.empty:

    max_weights = (
        strength_df.groupby("Exercise Name")["Weight"]
        .max()
        .reset_index()
        .sort_values("Exercise Name")
    )

    st.subheader("🏋️ Max Weight Per Exercise")
    st.dataframe(max_weights)

    # Last workout
    last_date = strength_df["Date"].max()
    last_workout = strength_df[strength_df["Date"] == last_date]

    trained_groups_last = set(
        body_groups.get(ex, "Unknown")
        for ex in last_workout["Exercise Name"].unique()
    )

    # Balanced recommendation
    group_counts = defaultdict(int)

    for ex in strength_df["Exercise Name"].unique():
        group = body_groups.get(ex, "Unknown")
        group_counts[group] += 1

    sorted_groups = sorted(group_counts.items(), key=lambda x: x[1])

    recommended = []

    for group, _ in sorted_groups:
        if group not in trained_groups_last:
            for ex, g in body_groups.items():
                if g == group:
                    recommended.append(ex)
                    break
        if len(recommended) == 5:
            break

    st.subheader("💡 Exercise Recommendation")

    if recommended:
        for ex in recommended:
            st.write("•", ex)
    else:
        st.write("All muscle groups were trained last session.")

# =============================
# CARDIO PARSING (EFFICIENT)
# =============================

def parse_tcx(filepath, activity_type):
    duration = 0
    distance = 0
    calories = 0
    hr_values = []
    start_time = None

    for event, elem in ET.iterparse(filepath, events=("end",)):
        tag = elem.tag.split("}")[-1]

        if tag == "Id" and start_time is None:
            start_time = datetime.fromisoformat(elem.text.replace("Z", "+00:00"))

        elif tag == "TotalTimeSeconds":
            duration += float(elem.text)

        elif tag == "DistanceMeters":
            distance += float(elem.text)

        elif tag == "Calories":
            calories += float(elem.text)

        elif tag == "Value":  # HR
            try:
                hr_values.append(int(elem.text))
            except:
                pass

        elem.clear()

    avg_hr = sum(hr_values) / len(hr_values) if hr_values else None
    max_hr = max(hr_values) if hr_values else None

    pace = None
    if distance > 0:
        pace = (duration / 60) / (distance / 1000)

    return {
        "Date": start_time,
        "Activity": activity_type,
        "Duration_min": duration / 60,
        "Distance_km": distance / 1000,
        "Calories": calories,
        "Avg_HR": avg_hr,
        "Max_HR": max_hr,
        "Pace_min_per_km": pace,
    }

# =============================
# LOAD CARDIO DATA
# =============================

cardio_records = []

for activity_type in ["running", "swimming", "walking"]:
    activity_path = os.path.join(CARDIO_FOLDER, activity_type)

    if os.path.exists(activity_path):
        for file in os.listdir(activity_path):
            if file.endswith(".tcx"):
                filepath = os.path.join(activity_path, file)
                try:
                    record = parse_tcx(filepath, activity_type.capitalize())
                    cardio_records.append(record)
                except:
                    pass

if cardio_records:
    cardio_df = pd.DataFrame(cardio_records)
else:
    cardio_df = pd.DataFrame()

# =============================
# CARDIO DASHBOARD
# =============================

st.header("🏃 Cardio Overview")

if not cardio_df.empty:

    cardio_df = cardio_df.sort_values("Date")

    st.subheader("📋 All Cardio Sessions")
    st.dataframe(cardio_df)

    st.subheader("📈 Weekly Distance")

    cardio_df["Week"] = cardio_df["Date"].dt.isocalendar().week
    weekly = cardio_df.groupby("Week")["Distance_km"].sum()

    st.bar_chart(weekly)

    st.subheader("⏱ Weekly Duration (min)")
    weekly_time = cardio_df.groupby("Week")["Duration_min"].sum()
    st.bar_chart(weekly_time)

else:
    st.write("No cardio data found.")
