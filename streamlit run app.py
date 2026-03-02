import streamlit as st
import pandas as pd
import json
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="Workout Tracker", layout="wide")

st.title("🏋️ Workout Tracker")

# ===============================
# LOAD BODY GROUP LIBRARY
# ===============================

BODY_GROUPS_FILE = "body_groups.json"

with open(BODY_GROUPS_FILE, "r") as f:
    body_groups = json.load(f)

# ===============================
# LOAD ALL TXT FILES FROM FOLDER
# ===============================

DATA_FOLDER = Path("Raw_data")
txt_files = sorted(DATA_FOLDER.glob("*.txt"))

if not txt_files:
    st.warning("No workout files found in Raw_data folder.")
    st.stop()

df_list = []

for file in txt_files:
    try:
        df = pd.read_csv(file, sep="\t")
        df.columns = df.columns.str.strip()

        # Extract date from filename (ddmmyy)
        workout_date = datetime.strptime(file.stem, "%d%m%y")
        df["Date"] = workout_date

        df.rename(columns={"Exercise Name": "Exercise"}, inplace=True)

        df_list.append(df)

    except Exception as e:
        st.warning(f"Skipping {file.name} due to error.")

df = pd.concat(df_list, ignore_index=True)

# ===============================
# CLEAN DATA
# ===============================

df["Weight"] = df["Weight"].str.replace(" kg", "").astype(float)
df["Volume"] = df["Volume"].str.replace(" kg", "").astype(float)

df["Body Group"] = df["Exercise"].map(body_groups)
df["Body Group"] = df["Body Group"].fillna("unknown")

# ===============================
# SHOW BASIC STATS
# ===============================

st.subheader("Workout Summary")

col1, col2, col3 = st.columns(3)

col1.metric("Total Workouts", df["Date"].nunique())
col2.metric("Total Exercises", df["Exercise"].nunique())
col3.metric("Total Volume", int(df["Volume"].sum()))

# ===============================
# VOLUME PER BODY GROUP
# ===============================

st.subheader("Volume per Body Group")

volume_group = (
    df.groupby("Body Group")["Volume"]
    .sum()
    .sort_values(ascending=False)
)

st.bar_chart(volume_group)

# ===============================
# RECOMMENDATION SYSTEM
# ===============================

st.subheader("Exercise Recommendation")

latest_date = df["Date"].max()
last_workout = df[df["Date"] == latest_date]

last_exercises = last_workout["Exercise"].unique()
last_body_groups = last_workout["Body Group"].unique()

# Avoid:
# - Exercises from last workout
# - Body groups trained last workout

recommend_df = df[
    (~df["Exercise"].isin(last_exercises)) &
    (~df["Body Group"].isin(last_body_groups))
]

if recommend_df.empty:
    st.info("No recommendation available. You trained everything recently 💪")
else:
    recommendation = (
        recommend_df.groupby("Exercise")["Volume"]
        .mean()
        .sort_values(ascending=False)
        .head(3)
        .index.tolist()
    )

    st.success("Recommended for today:")
    for ex in recommendation:
        st.write("•", ex)
