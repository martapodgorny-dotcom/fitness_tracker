import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import json
from datetime import datetime

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Workout Tracker", layout="wide")

DATA_DIRECTORY = Path(r"C:\Users\mp24aed\OneDrive - University of Hertfordshire\Desktop\Python codes\Work tracking\Raw_data")
BODY_GROUPS_FILE = DATA_DIRECTORY / "body_groups.json"

st.title("🏋️ Workout Tracker Dashboard")

# =========================
# LOAD DATA
# =========================
txt_files = sorted(DATA_DIRECTORY.glob("*.txt"))

if not txt_files:
    st.warning("No TXT files found in data directory.")
    st.stop()

df_list = []

for f in txt_files:
    df = pd.read_csv(f, sep="\t")
    df.columns = df.columns.str.strip()

    # Extract date from filename (ddmmyy)
    try:
        date_obj = datetime.strptime(f.stem, "%d%m%y")
    except:
        continue

    df["Date"] = date_obj
    df.rename(columns={"Exercise Name": "Exercise"}, inplace=True)
    df_list.append(df)

df = pd.concat(df_list, ignore_index=True)

# =========================
# PARSE WEIGHT
# =========================
def parse_weight(val):
    val = str(val).strip().lower()
    if "kg" in val:
        return float(val.replace(" kg", ""))
    elif "bodyweight" in val:
        return 75.0
    else:
        try:
            return float(val)
        except:
            return 0.0

df["weight_kg"] = df["Weight"].apply(parse_weight)
df["volume_kg"] = df["Volume"].apply(parse_weight)
df["Reps"] = df["Reps"].astype(int)

# =========================
# BODY GROUP MEMORY
# =========================
if BODY_GROUPS_FILE.exists():
    with open(BODY_GROUPS_FILE, "r") as f:
        body_groups = json.load(f)
else:
    body_groups = {}

st.sidebar.header("Body Group Settings")

for ex in sorted(df["Exercise"].unique()):
    if ex not in body_groups:
        body_groups[ex] = st.sidebar.selectbox(
            f"Assign body group for {ex}",
            ["legs", "core", "arms"],
            key=ex
        )

with open(BODY_GROUPS_FILE, "w") as f:
    json.dump(body_groups, f, indent=2)

df["body_group"] = df["Exercise"].map(body_groups)

# =========================
# LAST & MAX TABLE
# =========================
st.subheader("📊 Last & Max Weights")

exercise_table = df.groupby("Exercise").agg(
    Last_Weight=("weight_kg", "last"),
    Max_Weight=("weight_kg", "max")
).sort_index()

st.dataframe(exercise_table, use_container_width=True)

# =========================
# MAX WEIGHT BAR CHART
# =========================
st.subheader("🏆 Maximum Weight per Exercise")

max_weights = df.groupby("Exercise")["weight_kg"].max().sort_values(ascending=False)

fig, ax = plt.subplots(figsize=(10, 5))
max_weights.plot(kind="bar", ax=ax)
ax.set_ylabel("Max Weight (kg)")
ax.set_xlabel("Exercise")
ax.set_title("Maximum Weight per Exercise")
plt.xticks(rotation=45)
st.pyplot(fig)

# =========================
# RECOMMENDATION ENGINE
# =========================
st.subheader("🔥 Next Session Recommendations")

last_session_date = df["Date"].max()
last_session_exercises = df[df["Date"] == last_session_date]["Exercise"].unique()

group_sets = df.groupby("body_group").size()
group_pct = group_sets / group_sets.sum()
min_pct = group_pct.min()
undertrained_groups = group_pct[group_pct == min_pct].index.tolist()

recommended_exercises = []

for group in undertrained_groups:
    ex_list = df[df["body_group"] == group].copy()

    # ❌ Exclude last session exercises
    ex_list = ex_list[~ex_list["Exercise"].isin(last_session_exercises)]

    ex_list["last_weight"] = ex_list.groupby("Exercise")["weight_kg"].transform("last")
    ex_unique = ex_list.drop_duplicates("Exercise").sort_values("last_weight")

    for _, row in ex_unique.iterrows():
        max_weight = df[df["Exercise"] == row["Exercise"]]["weight_kg"].max()
        recommended_exercises.append(
            (row["Exercise"], group, row["last_weight"], max_weight)
        )
        if len(recommended_exercises) == 5:
            break
    if len(recommended_exercises) == 5:
        break

if not recommended_exercises:
    st.info("Not enough exercises available (all were done last session).")
else:
    for ex, group, last_w, max_w in recommended_exercises:
        st.write(f"**{ex}** ({group}) — Last: {last_w} kg | Max: {max_w} kg")

st.success("Dashboard updated successfully.")