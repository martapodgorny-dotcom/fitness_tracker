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

with open("body_groups.json", "r") as f:
    body_groups = json.load(f)

# ===============================
# LOAD DATA FILES
# ===============================

DATA_FOLDER = Path("Raw_data")
txt_files = sorted(DATA_FOLDER.glob("*.txt"))

if not txt_files:
    st.warning("No workout files found.")
    st.stop()

df_list = []

def parse_date_from_filename(filename):
    name = filename.stem
    
    # Try strict DDMMYY
    try:
        return datetime.strptime(name, "%d%m%y")
    except:
        pass
    
    # Try without leading zero (e.g. 20226 for 2 Feb 26)
    try:
        if len(name) == 5:
            day = int(name[0])
            month = int(name[1:3])
            year = int("20" + name[3:])
            return datetime(year, month, day)
    except:
        pass

    return None

for file in txt_files:
    try:
        df = pd.read_csv(file, sep="\t")
        df.columns = df.columns.str.strip()

        workout_date = parse_date_from_filename(file)

        if workout_date is None:
            st.warning(f"Could not parse date from {file.name}")
            continue

        df["Date"] = workout_date
        df.rename(columns={"Exercise Name": "Exercise"}, inplace=True)
        df_list.append(df)

    except Exception:
        st.warning(f"Skipping {file.name}")

if not df_list:
    st.error("No valid workout data.")
    st.stop()

df = pd.concat(df_list, ignore_index=True)

# ===============================
# CLEAN NUMERIC COLUMNS
# ===============================

def clean_kg(series):
    return pd.to_numeric(
        series.astype(str)
        .str.replace("kg", "", regex=False)
        .str.replace(" ", "", regex=False),
        errors="coerce"
    )

df["Weight"] = clean_kg(df["Weight"])
df["Volume"] = clean_kg(df["Volume"])

df["Body Group"] = df["Exercise"].map(body_groups).fillna("unknown")

# ===============================
# DEBUG DATE CHECK
# ===============================

st.write("Detected workout dates:")
st.write(sorted(df["Date"].unique()))

# ===============================
# WORKOUT SUMMARY
# ===============================

st.subheader("Workout Summary")

col1, col2, col3 = st.columns(3)
col1.metric("Total Workouts", df["Date"].nunique())
col2.metric("Total Exercises", df["Exercise"].nunique())
col3.metric("Total Volume", int(df["Volume"].sum(skipna=True)))

# ===============================
# TABLE: LAST & MAX WEIGHT
# ===============================

st.subheader("Exercise Progress")

last_weights = (
    df.sort_values("Date")
      .groupby("Exercise")
      .tail(1)
      .set_index("Exercise")["Weight"]
)

max_weights = df.groupby("Exercise")["Weight"].max()

progress_df = pd.DataFrame({
    "Last Weight": last_weights,
    "Max Weight": max_weights
}).sort_values("Max Weight", ascending=False)

st.dataframe(progress_df)

# ===============================
# STATS PER BODY GROUP
# ===============================

st.subheader("Body Group Statistics")

group_stats = df.groupby("Body Group").agg({
    "Weight": "mean",
    "Reps": "sum",
    "Exercise": "count"
}).rename(columns={
    "Weight": "Average Weight",
    "Reps": "Total Reps",
    "Exercise": "Total Sets"
})

st.dataframe(group_stats)

st.subheader("Volume per Body Group")
volume_group = df.groupby("Body Group")["Volume"].sum()
st.bar_chart(volume_group)

# ===============================
# RECOMMENDATIONS
# ===============================

st.subheader("Exercise Recommendation")

latest_date = df["Date"].max()
last_workout = df[df["Date"] == latest_date]

last_exercises = last_workout["Exercise"].unique()
last_body_groups = last_workout["Body Group"].unique()

recommend_df = df[
    (~df["Exercise"].isin(last_exercises)) &
    (~df["Body Group"].isin(last_body_groups))
]

if recommend_df.empty:
    st.warning("No recommendation available — all muscle groups were trained last session.")
else:
    recommendation = (
        recommend_df.groupby("Exercise")["Weight"]
        .mean()
        .sort_values(ascending=False)
        .head(3)
        .index.tolist()
    )

    st.success("Recommended for today:")
    for ex in recommendation:
        st.write("•", ex)
