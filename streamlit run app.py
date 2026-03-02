# gym_tracker_app.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import json
from datetime import datetime
import io

st.set_page_config(page_title="Gym Tracker", layout="wide")

# =========================
# FILE UPLOAD
# =========================
st.title("Gym Tracker")

uploaded_files = st.file_uploader(
    "Upload your workout TXT files",
    type="txt",
    accept_multiple_files=True
)

if not uploaded_files:
    st.info("Upload TXT files to start processing.")
    st.stop()

# =========================
# BODY GROUP MEMORY FILE
# =========================
BODY_GROUPS_FILE = Path("body_groups.json")
if BODY_GROUPS_FILE.exists():
    with open(BODY_GROUPS_FILE, "r") as f:
        body_groups = json.load(f)
else:
    body_groups = {}

# =========================
# READ AND PARSE FILES
# =========================
df_list = []
for uploaded_file in uploaded_files:
    df = pd.read_csv(uploaded_file, sep="\t")
    df.columns = df.columns.str.strip()  # remove spaces in header

    # Extract date from filename
    date_str = Path(uploaded_file.name).stem
    if len(date_str) == 6:
        date_obj = datetime.strptime(date_str, "%d%m%y")
    else:
        date_obj = datetime.now()
    df["Date"] = date_obj

    df.rename(columns={"Exercise Name":"Exercise", "Reps":"Reps", "Weight":"Weight", "Volume":"Volume"}, inplace=True)
    df_list.append(df)

df = pd.concat(df_list, ignore_index=True)

# =========================
# PARSE WEIGHT AND VOLUME
# =========================
def parse_weight(val):
    val = str(val)
    if "kg" in val:
        return float(val.replace(" kg",""))
    elif "Bodyweight" in val:
        return 75.0  # default bodyweight
    else:
        return float(val)

df["weight_kg"] = df["Weight"].apply(parse_weight)
df["volume_kg"] = df["Volume"].apply(parse_weight)
df["Reps"] = df["Reps"].astype(int)

# =========================
# BODY GROUP ASSIGNMENT
# =========================
for ex in sorted(df["Exercise"].unique()):
    if ex not in body_groups:
        group = st.selectbox(f"Assign body group for '{ex}'", ["legs", "core", "arms"])
        body_groups[ex] = group

# Save updated memory
with open(BODY_GROUPS_FILE, "w") as f:
    json.dump(body_groups, f, indent=2)

df["body_group"] = df["Exercise"].map(body_groups)

# =========================
# LAST AND MAX WEIGHTS TABLE
# =========================
exercise_table = df.groupby("Exercise").agg(
    Last_Weight=("weight_kg","last"),
    Max_Weight=("weight_kg","max")
).sort_index()

st.subheader("Last and Max Weights per Exercise")
st.dataframe(exercise_table)

# Save as image
fig, ax = plt.subplots(figsize=(8, len(exercise_table)*0.4 + 1))
ax.axis("off")
table_data = exercise_table.reset_index()
table = ax.table(cellText=table_data.values, colLabels=table_data.columns, loc="center")
table.auto_set_font_size(False)
table.set_fontsize(10)
table.auto_set_column_width(col=list(range(len(table_data.columns))))
plt.tight_layout()
plt.savefig("exercise_last_max_weights.png")
plt.close()

# =========================
# WEIGHT PROGRESSION PLOTS
# =========================
st.subheader("Weight Progression per Exercise")
for ex in df["Exercise"].unique():
    ex_df = df[df["Exercise"]==ex].sort_values("Date")
    fig, ax = plt.subplots()
    ax.plot(ex_df["Date"], ex_df["weight_kg"], marker="o")
    ax.set_xlabel("Date")
    ax.set_ylabel("Weight (kg)")
    ax.set_title(f"{ex} – Weight progression")
    plt.xticks(rotation=45)
    st.pyplot(fig)
    plt.close()

# =========================
# MAX WEIGHT PER EXERCISE BAR PLOT
# =========================
st.subheader("Maximum Weight per Exercise")
max_weights = df.groupby("Exercise")["weight_kg"].max().sort_values(ascending=False)
fig, ax = plt.subplots(figsize=(10,6))
max_weights.plot(kind="bar", color="skyblue", ax=ax)
ax.set_ylabel("Max Weight (kg)")
ax.set_xlabel("Exercise")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
st.pyplot(fig)
plt.close()

# =========================
# AVERAGE SETS PER EXERCISE
# =========================
st.subheader("Average Sets per Exercise")
total_sessions = df["Date"].nunique()
avg_sets_per_exercise = df.groupby("Exercise").size() / total_sessions
fig, ax = plt.subplots(figsize=(10,6))
avg_sets_per_exercise.sort_values(ascending=False).plot(kind="bar", color="lightcoral", ax=ax)
ax.set_ylabel("Average Sets per Session")
ax.set_xlabel("Exercise")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
st.pyplot(fig)
plt.close()

# =========================
# BODY GROUP SUMMARY
# =========================
st.subheader("Body Group Summary")
group_summary = (
    df.groupby("body_group")
    .agg(total_volume=("volume_kg","sum"),
         total_reps=("Reps","sum"),
         sessions_done=("Date","nunique"))
    .reset_index()
)
group_summary["avg_volume_per_session"] = group_summary["total_volume"]/group_summary["sessions_done"]
group_summary["avg_reps_per_session"] = group_summary["total_reps"]/group_summary["sessions_done"]

fig, ax = plt.subplots()
ax.bar(group_summary["body_group"], group_summary["total_volume"], color=["skyblue","lightgreen","salmon"])
ax.set_ylabel("Total Volume (kg)")
ax.set_xlabel("Body Group")
ax.set_title("Total Volume per Body Group")
plt.tight_layout()
st.pyplot(fig)
plt.close()

# =========================
# NEXT SESSION RECOMMENDATION (5 exercises)
# =========================
st.subheader("Next Session Recommendations")

# Avoid exercises done in last session
last_date = df["Date"].max()
last_exercises = df[df["Date"]==last_date]["Exercise"].unique()

# Calculate undertrained groups
group_sets = df.groupby("body_group").size()
group_pct = group_sets / group_sets.sum()
min_pct = group_pct.min()
undertrained_groups = group_pct[group_pct==min_pct].index.tolist()

# Pick 5 exercises avoiding last session
recommended_exercises = []
for group in undertrained_groups:
    for ex in df[df["body_group"]==group]["Exercise"].unique():
        if ex not in last_exercises:
            last_weight = df[df["Exercise"]==ex]["weight_kg"].iloc[-1]
            max_weight = df[df["Exercise"]==ex]["weight_kg"].max()
            recommended_exercises.append((ex, group, last_weight, max_weight))
recommended_exercises = recommended_exercises[:5]

# Display recommendations
for ex, group, last_w, max_w in recommended_exercises:
    st.write(f"{ex} ({group}) – Last: {last_w} kg, Max: {max_w} kg")
