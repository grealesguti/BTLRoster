import streamlit as st
import pandas as pd
import os
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# -------------------
# CONFIG
# -------------------
newdle_folder = "Newdles"
save_folder = "weekly_rosters"
os.makedirs(save_folder, exist_ok=True)

# -------------------
# Load newest CSV from Newdles
# -------------------
csv_files = [f for f in os.listdir(newdle_folder) if f.endswith(".csv")]
if not csv_files:
    st.error("No CSV files found in Newdles folder.")
    st.stop()

newest_csv = max(csv_files, key=lambda f: os.path.getmtime(os.path.join(newdle_folder, f)))
availability_csv = os.path.join(newdle_folder, newest_csv)
st.info(f"Using newest CSV: {availability_csv}")

availability_df = pd.read_csv(availability_csv)

employees = sorted(availability_df['Name'].unique())
days = sorted(availability_df['Day'].unique())
shift_hours = sorted(availability_df['Hour'].unique())

activities = ["None", "Cleaning", "Maintenance", "Support", "Inventory"]

# Colors
colors = plt.cm.tab10.colors
employee_colors = {emp: colors[i % len(colors)] for i, emp in enumerate(employees)}
activity_colors = plt.cm.Set2.colors
activity_colors_dict = {act: activity_colors[i % len(activity_colors)] if act != "None" else "gray"
                        for i, act in enumerate(activities)}

# Map availability
availability_map = {day:{} for day in days}
for _, row in availability_df.iterrows():
    if str(row['Availability']).strip().lower() == "available":
        availability_map[row['Day']].setdefault(row['Hour'], []).append(row['Name'])

# -------------------
# Prefill from last roster CSV
# -------------------
roster_files = [f for f in os.listdir(save_folder) if f.endswith(".csv")]
latest_roster_df = None
if roster_files:
    latest_roster = max(roster_files, key=lambda f: os.path.getmtime(os.path.join(save_folder, f)))
    latest_roster_df = pd.read_csv(os.path.join(save_folder, latest_roster))
    st.success(f"Prefilling from last roster: {latest_roster}")
else:
    st.warning("No previous roster found, starting empty.")

# -------------------
# Always show latest JPG
# -------------------
jpg_files = [f for f in os.listdir(save_folder) if f.endswith(".jpg")]
if jpg_files:
    latest_jpg = max(jpg_files, key=lambda f: os.path.getmtime(os.path.join(save_folder, f)))
    st.image(os.path.join(save_folder, latest_jpg), caption=f"Latest roster image ({latest_jpg})", use_container_width=True)
else:
    st.warning("No roster images found yet.")

# -------------------
# Build interactive editor
# -------------------
st.header("Roster Editor")

def colored_selectbox(label, options, index=0):
    # Determine color based on selection
    color = "#d0f0c0" if options[index] != "None" else "#ffffff"  # light green if selected
    container = f"""
    <div style="background-color: {color}; padding:2px; border-radius:4px">
        {st.selectbox(label, options, index=index, key=label)}
    </div>
    """
    st.markdown(container, unsafe_allow_html=True)


roster_data = []
for day in days:
    st.subheader(day)
    for hour in shift_hours:
        cols = st.columns([1, 2, 2, 2, 2, 2, 2])
        cols[0].write(hour)

        available_emps = availability_map.get(day, {}).get(hour, [])
        prefill = available_emps[:4] + ["None"]*(4-len(available_emps[:4]))

        # Prefill activities from last roster
        activity1_value, activity2_value = "None", "None"
        if latest_roster_df is not None:
            row = latest_roster_df[(latest_roster_df['Day'] == day) & (latest_roster_df['Hour'] == hour)]
            if not row.empty:
                activity1_value = row['Activity1'].values[0]
                activity2_value = row['Activity2'].values[0]

        emp1 = cols[1].selectbox("Emp1", ["None"] + employees, index=(["None"]+employees).index(prefill[0]), key=f"{day}_{hour}_emp1")
        emp2 = cols[2].selectbox("Emp2", ["None"] + employees, index=(["None"]+employees).index(prefill[1]), key=f"{day}_{hour}_emp2")
        emp3 = cols[3].selectbox("Emp3", ["None"] + employees, index=(["None"]+employees).index(prefill[2]), key=f"{day}_{hour}_emp3")
        emp4 = cols[4].selectbox("Emp4", ["None"] + employees, index=(["None"]+employees).index(prefill[3]), key=f"{day}_{hour}_emp4")

        act1 = cols[5].selectbox("Act1", activities, index=activities.index(activity1_value), key=f"{day}_{hour}_act1")
        act2 = cols[6].selectbox("Act2", activities, index=activities.index(activity2_value), key=f"{day}_{hour}_act2")

        roster_data.append([day, hour, emp1, emp2, act1, emp3, emp4, act2])

# -------------------
# Save & Plot
# -------------------
def save_and_plot():
    df = pd.DataFrame(roster_data, columns=["Day", "Hour", "Employee1", "Employee2", "Activity1",
                                            "Employee3", "Employee4", "Activity2"])
    date_str = datetime.now().strftime("%Y-%m-%d_%H%M")
    csv_path = os.path.join(save_folder, f"roster_{date_str}.csv")
    df.to_csv(csv_path, index=False)

    # Plot
    fig, ax = plt.subplots(figsize=(12,6))
    bar_width = 0.5
    day_positions = range(len(days))

    for day_idx, day in enumerate(days):
        for hour_idx, hour in enumerate(shift_hours):
            row = df[(df["Day"]==day) & (df["Hour"]==hour)].iloc[0]
            start_hour = int(hour.split(":")[0])
            height = 0.3

            for i, (emp, act) in enumerate([(row.Employee1, row.Activity1),
                                            (row.Employee2, row.Activity1),
                                            (row.Employee3, row.Activity2),
                                            (row.Employee4, row.Activity2)]):
                ax.bar(day_idx, height, bottom=start_hour + i*height, width=bar_width,
                       color=employee_colors.get(emp,'gray'))
                ax.text(day_idx, start_hour + (i+0.5)*height, f"{emp}\n{act}", ha='center', va='center',
                        color='black' if emp=="None" else 'white', fontsize=7)

    ax.set_xticks(list(day_positions))
    ax.set_xticklabels(days)
    ax.set_ylabel("Hour")
    ax.set_title("Weekly Schedule")
    ax.grid(True, axis='y', linestyle='--', alpha=0.5)

    emp_patches = [mpatches.Patch(color=color, label=emp) for emp,color in employee_colors.items() if emp!="None"]
    act_patches = [mpatches.Patch(edgecolor=color, facecolor='none', label=act, linewidth=2)
                   for act,color in activity_colors_dict.items() if act!="None"]
    ax.legend(handles=emp_patches + act_patches, bbox_to_anchor=(1.05,1), loc='upper left')

    plt.tight_layout()
    img_path = os.path.join(save_folder, f"roster_{date_str}.jpg")
    plt.savefig(img_path, dpi=300)
    st.pyplot(fig)

    st.success(f"Roster saved to {csv_path} and {img_path}")

if st.button("💾 Save Roster & Generate Plot"):
    save_and_plot()
