import streamlit as st
import pandas as pd
import os
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import html
from datetime import datetime
from ics import Calendar, Event
from datetime import datetime, timedelta
import streamlit as st
import requests
import streamlit as st
from urllib.parse import urlparse


# -------------------
# CONFIG
# -------------------
NEWDLE_FOLDER = "Newdles"


SAVE_FOLDER = "weekly_rosters"
AVAILABILITY_FOLDER = "Availability"

os.makedirs(SAVE_FOLDER, exist_ok=True)
os.makedirs(AVAILABILITY_FOLDER, exist_ok=True)

WEBHOOK_URL = "https://mattermost.web.cern.ch/hooks/fr7t634m9jbqmmjkgpz7knhnih"
CHANNEL_ID = "hgyg9i1effg8pd8ser3kuowueh"  # optional
SCHEDULE_WEBPAGE_URL = "https://yourwebsite.com/weekly-roster"  # replace with your URL
PASSWORD = "mypassword123"  # Replace with your desired password
activities = ["None", "Cabling ETH", "Airex Foiling", "Airex Modif.","Airex Gluing", "Beam Precal.", "Grounding Strips"]

# -------------------
# Utility functions
# -------------------
def select_old_csv(save_folder):
    # List all CSV files
    csv_files = [f for f in os.listdir(save_folder) if f.endswith(".csv")]
    if not csv_files:
        st.warning("No previous roster CSVs found.")
        return None

    csv_files.sort(reverse=True)  # show latest first
    # Dropdown selectbox
    selected_csv = st.selectbox("Select a previous roster CSV", csv_files)
    df = pd.read_csv(os.path.join(save_folder, selected_csv))
    st.info(f"Loaded CSV: {selected_csv}")
    return df
def select_old_jpg(save_folder):
    jpg_files = [f for f in os.listdir(save_folder) if f.endswith(".jpg")]
    if not jpg_files:
        st.warning("No previous roster images found.")
        return None

    jpg_files.sort(reverse=True)
    selected_jpg = st.selectbox("Select a previous roster image", jpg_files)
    st.image(os.path.join(save_folder, selected_jpg), caption=f"Roster image: {selected_jpg}", use_container_width=True)
    return selected_jpg


def save_csv_file(uploaded_file, folder):
    """Save uploaded CSV to folder."""
    path = os.path.join(folder, uploaded_file.name)
    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return path

def get_latest_csv(folder):
    """Return the newest CSV file in a folder."""
    csv_files = glob(os.path.join(folder, "*.csv"))
    if not csv_files:
        return None
    return max(csv_files, key=os.path.getmtime)

def upload_and_process_newdle_csv():
    """Upload a CSV and process it into availability format."""
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
    if uploaded_file is not None:
        saved_path = save_csv_file(uploaded_file, SAVE_FOLDER)
        st.success(f"Uploaded {uploaded_file.name}")

        # Process CSV into availability format
        df = pd.read_csv(saved_path)
        time_slots = [col for col in df.columns if col not in ["Participant name", "Comment"]]
        rows = []
        for _, row in df.iterrows():
            name = row["Participant name"]
            for ts in time_slots:
                day, hour = ts.split("T")
                availability = str(row[ts]).strip().lower()
                if availability not in ["available", "unavailable"]:
                    availability = "unavailable"
                rows.append([day, hour, name, availability])

        availability_df = pd.DataFrame(rows, columns=["Day", "Hour", "Name", "Availability"])
        
        # Save processed availability
        avail_path = os.path.join(AVAILABILITY_FOLDER, "availability_extracted.csv")
        availability_df.to_csv(avail_path, index=False)
        st.info(f"Processed availability saved to {avail_path}")
        return availability_df
    return None

# -------------------
# Load the latest availability
# -------------------
def load_latest_availability_csv(folder: str):
    """Load the newest CSV in the availability folder."""
    csv_files = [f for f in os.listdir(folder) if f.endswith(".csv")]
    if not csv_files:
        st.error(f"No CSV files found in {folder}.")
        st.stop()
    newest_csv = max(csv_files, key=lambda f: os.path.getmtime(os.path.join(folder, f)))
    st.info(f"Using newest CSV: {os.path.join(folder, newest_csv)}")
    return pd.read_csv(os.path.join(folder, newest_csv))

# -------------------
# Map availability
# -------------------
def create_availability_map(df):
    """Convert availability DataFrame into a dictionary for roster prefill."""
    availability_map = {day:{} for day in df['Day'].unique()}
    for _, row in df.iterrows():
        if str(row['Availability']).strip().lower() == "available":
            availability_map[row['Day']].setdefault(row['Hour'], []).append(row['Name'])
    return availability_map

def get_newdle_title(link: str) -> str:
    """Fetch the Newdle title using the exact URL provided."""
    if not link.strip():
        return ""
    try:
        # Only process CERN Newdle links
        parsed = urlparse(link)
        if "newdle.cern.ch" not in parsed.netloc:
            return "External link"
        
        # Extract the code: last segment if not 'summary'
        path_parts = parsed.path.strip("/").split("/")
        code = path_parts[-1] if path_parts[-1] != "summary" else path_parts[-2]

        api_url = f"https://newdle.cern.ch/api/newdle/{code}"
        resp = requests.get(api_url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get("title", "Untitled Newdle")
    except Exception as e:
        print(f"Error fetching title for {link}: {e}")
        return "Unavailable"



def extract_newdle_availability(newdle_folder="Newdles", save_folder="availability_extracted"):
    """
    Extracts availability data from the latest Newdle CSV, saves it to a new folder with a timestamped filename,
    and returns the extracted DataFrame.
    """
    # Ensure save folder exists
    os.makedirs(save_folder, exist_ok=True)

    # Find all CSV files in the Newdle folder
    csv_files = glob(os.path.join(newdle_folder, "*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in folder '{newdle_folder}'")

    # Get the newest CSV by modification time
    newest_csv = max(csv_files, key=os.path.getmtime)
    print(f"Using newest CSV: {newest_csv}")

    # Load CSV
    df = pd.read_csv(newest_csv)

    # Identify time slot columns
    time_slots = [col for col in df.columns if col not in ['Participant name', 'Comment']]

    # Extract availability
    rows = []
    for _, row in df.iterrows():
        name = row['Participant name']
        for ts in time_slots:
            try:
                day, hour = ts.split("T")
            except ValueError:
                # Skip malformed columns
                continue
            availability = str(row[ts]).strip().lower()
            if availability not in ['available', 'unavailable']:
                availability = 'unavailable'  # treat empty or other values as unavailable
            rows.append([day, hour, name, availability])

    # Convert to DataFrame
    availability_df = pd.DataFrame(rows, columns=['Day', 'Hour', 'Name', 'Availability'])

    # Save CSV with date in filename
    date_str = datetime.now().strftime("%Y-%m-%d_%H%M")
    output_file = os.path.join(save_folder, f"availability_{date_str}.csv")
    availability_df.to_csv(output_file, index=False)

    print(f"Availability extracted and saved to {output_file}")
    return availability_df

def load_latest_newdle_csv():
    csv_files = [f for f in os.listdir(NEWDLE_FOLDER) if f.endswith(".csv")]
    if not csv_files:
        return None
    newest_csv = max(csv_files, key=lambda f: os.path.getmtime(os.path.join(NEWDLE_FOLDER, f)))
    return pd.read_csv(os.path.join(NEWDLE_FOLDER, newest_csv))

def get_latest_roster_csv(save_folder):
    """Return the path of the latest CSV in the folder."""
    csv_files = [f for f in os.listdir(save_folder) if f.endswith(".csv")]
    if not csv_files:
        return None
    latest_csv = max(csv_files, key=lambda f: os.path.getmtime(os.path.join(save_folder, f)))
    return os.path.join(save_folder, latest_csv)

def generate_employee_ics_from_csv(csv_path, employee_name):
    """Generate an ICS calendar file for the specified employee from a CSV."""
    df = pd.read_csv(csv_path)
    c = Calendar()
    for _, row in df.iterrows():
        day = row['Day']
        hour = row['Hour']
        emp_activity_pairs = [(row['Employee1'], row['Activity1']),
                              (row['Employee2'], row['Activity1']),
                              (row['Employee3'], row['Activity2']),
                              (row['Employee4'], row['Activity2'])]
        for emp, act in emp_activity_pairs:
            if emp == employee_name and act != "None":
                start_dt = datetime.strptime(f"{day} {hour}", "%Y-%m-%d %H:%M")
                end_dt = start_dt + timedelta(hours=1)  # assume 1-hour shifts
                e = Event()
                e.name = f"Shift: {act}"
                e.begin = start_dt
                e.end = end_dt
                c.events.add(e)
    return c

def generate_employee_ics(roster_data, employee_name):
    """
    Generate an ICS calendar file for the specified employee.
    roster_data: list of [day, hour, emp1, emp2, act1, emp3, emp4, act2]
    """
    c = Calendar()

    for row in roster_data:
        day, hour, emp1, emp2, act1, emp3, emp4, act2 = row

        # Determine if the employee is scheduled in this shift
        emp_activity_pairs = [(emp1, act1), (emp2, act1), (emp3, act2), (emp4, act2)]
        for emp, act in emp_activity_pairs:
            if emp == employee_name and act != "None":
                # Parse day and hour
                start_dt = datetime.strptime(f"{day} {hour}", "%Y-%m-%d %H:%M")
                end_dt = start_dt + timedelta(hours=1)  # assuming 1 hour shifts

                e = Event()
                e.name = f"Shift: {act}"
                e.begin = start_dt
                e.end = end_dt
                c.events.add(e)

    return c
def send_schedule_notification():
    """Send a Mattermost message announcing a new schedule."""
    message_text = f"A new weekly schedule is available! Check it here: {SCHEDULE_WEBPAGE_URL}"
    payload = {
        "channel_id": CHANNEL_ID,
        "text": message_text
    }
    response = requests.post(WEBHOOK_URL, json=payload)
    if response.status_code == 200:
        st.success("Message sent successfully!")
    else:
        st.error(f"Failed to send message: {response.status_code} {response.text}")
def save_uploaded_csv(uploaded_file, folder):
    """Save uploaded CSV to folder with timestamped name."""
    date_str = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    save_path = os.path.join(folder, f"uploaded_{date_str}.csv")
    with open(save_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.success(f"Uploaded CSV saved to {save_path}")
    return save_path

def get_newest_csv(folder):
    """Return path to the newest CSV in a folder."""
    csv_files = [f for f in os.listdir(folder) if f.endswith(".csv")]
    if not csv_files:
        st.error(f"No CSV files found in {folder}.")
        st.stop()
    newest_csv = max(csv_files, key=lambda f: os.path.getmtime(os.path.join(folder, f)))
    return os.path.join(folder, newest_csv)



def load_newest_csv(folder: str):
    csv_files = [f for f in os.listdir(folder) if f.endswith(".csv")]
    if not csv_files:
        st.error(f"No CSV files found in {folder}.")
        st.stop()
    newest_csv = max(csv_files, key=lambda f: os.path.getmtime(os.path.join(folder, f)))
    st.info(f"Using newest CSV: {os.path.join(folder, newest_csv)}")
    return pd.read_csv(os.path.join(folder, newest_csv))

def get_last_roster(folder: str):
    roster_files = [f for f in os.listdir(folder) if f.endswith(".csv")]
    if roster_files:
        latest_roster = max(roster_files, key=lambda f: os.path.getmtime(os.path.join(folder, f)))
        st.success(f"Prefilling from last roster: {latest_roster}")
        return pd.read_csv(os.path.join(folder, latest_roster))
    st.warning("No previous roster found, starting empty.")
    return None

def show_latest_image(folder: str):
    jpg_files = [f for f in os.listdir(folder) if f.endswith(".jpg")]
    if jpg_files:
        latest_jpg = max(jpg_files, key=lambda f: os.path.getmtime(os.path.join(folder, f)))
        st.image(os.path.join(folder, latest_jpg), caption=f"Latest roster image ({latest_jpg})", use_container_width=True)
    else:
        st.warning("No roster images found yet.")

def map_availability(df):
    availability_map = {day:{} for day in df['Day'].unique()}
    for _, row in df.iterrows():
        if str(row['Availability']).strip().lower() == "available":
            availability_map[row['Day']].setdefault(row['Hour'], []).append(row['Name'])
    return availability_map
def build_roster_editor(days, shift_hours, employees, activities, availability_map, latest_roster_df):
    roster_data = []
    st.header("Roster Editor")

    def colored_selectbox(label, options, selected_value, key):
        """Returns a selectbox with a colored background if value is not 'None'."""
        index = options.index(selected_value)
        # Light green if selected, white if 'None'
        color = "#d0f0c0" if selected_value != "None" else "#ffffff"
        container = f"""
        <div style="background-color: {color}; padding:2px; border-radius:4px">
            {st.selectbox(label, options, index=index, key=key)}
        </div>
        """
        return st.markdown(container, unsafe_allow_html=True)

    for day in days:
        # Add day of the week next to the date
        try:
            day_dt = datetime.strptime(day, "%Y-%m-%d")  # adjust format if different
            weekday = day_dt.strftime("%A")
            day_label = f"{day} ({weekday})"
        except:
            day_label = day  # fallback if parsing fails

        st.subheader(day_label)

        for hour in shift_hours:
            cols = st.columns([1,2,2,2,2,2,2])
            cols[0].write(hour)

            available_emps = availability_map.get(day, {}).get(hour, [])
            prefill = available_emps[:4] + ["None"]*(4-len(available_emps[:4]))

            # Prefill activities
            activity1_value, activity2_value = "None", "None"
            if latest_roster_df is not None:
                row = latest_roster_df[(latest_roster_df['Day'] == day) & (latest_roster_df['Hour'] == hour)]
                if not row.empty:
                    activity1_value = row['Activity1'].values[0]
                    activity2_value = row['Activity2'].values[0]

            # Use colored selectboxes
            emp1 = cols[1].selectbox("Emp1", ["None"]+employees, index=(["None"]+employees).index(prefill[0]), key=f"{day}_{hour}_emp1")
            emp2 = cols[2].selectbox("Emp2", ["None"]+employees, index=(["None"]+employees).index(prefill[1]), key=f"{day}_{hour}_emp2")
            emp3 = cols[3].selectbox("Emp3", ["None"]+employees, index=(["None"]+employees).index(prefill[2]), key=f"{day}_{hour}_emp3")
            emp4 = cols[4].selectbox("Emp4", ["None"]+employees, index=(["None"]+employees).index(prefill[3]), key=f"{day}_{hour}_emp4")

            act1 = cols[5].selectbox("Act1", activities, index=activities.index(activity1_value), key=f"{day}_{hour}_act1")
            act2 = cols[6].selectbox("Act2", activities, index=activities.index(activity2_value), key=f"{day}_{hour}_act2")

            # Highlight selected values
            for col, val, k in zip(cols[1:], [emp1, emp2, emp3, emp4, act1, act2],
                                   [f"{day}_{hour}_emp1", f"{day}_{hour}_emp2", f"{day}_{hour}_emp3", f"{day}_{hour}_emp4",
                                    f"{day}_{hour}_act1", f"{day}_{hour}_act2"]):
                if val != "None":
                    col.markdown(f'<div style="background-color:#d0f0c0; border-radius:4px; padding:2px">{val}</div>', unsafe_allow_html=True)

            roster_data.append([day, hour, emp1, emp2, act1, emp3, emp4, act2])

    return roster_data

def save_and_plot(roster_data, days, shift_hours, employee_colors, activity_colors_dict, save_folder):
    df = pd.DataFrame(roster_data, columns=["Day", "Hour", "Employee1", "Employee2", "Activity1",
                                            "Employee3", "Employee4", "Activity2"])
    date_str = datetime.now().strftime("%Y-%m-%d_%H%M")
    csv_path = os.path.join(save_folder, f"roster_{date_str}.csv")
    df.to_csv(csv_path, index=False)

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

    # Invert y-axis
    ax.invert_yaxis()

    # Only show initial and final hours
    start_hour = int(shift_hours[0].split(":")[0])
    end_hour = int(shift_hours[-1].split(":")[0])
    ax.set_yticks([start_hour, end_hour])
    ax.set_yticklabels([shift_hours[0], shift_hours[-1]])

    # Legend
    emp_patches = [mpatches.Patch(color=color, label=emp) for emp,color in employee_colors.items() if emp!="None"]
    act_patches = [mpatches.Patch(edgecolor=color, facecolor='none', label=act, linewidth=2)
                   for act,color in activity_colors_dict.items() if act!="None"]
    ax.legend(handles=emp_patches + act_patches, bbox_to_anchor=(1.05,1), loc='upper left')

    plt.tight_layout()
    img_path = os.path.join(save_folder, f"roster_{date_str}.jpg")
    plt.savefig(img_path, dpi=300)
    st.pyplot(fig)
    st.success(f"Roster saved to {csv_path} and {img_path}")
    
# -------------------
# Function to preview roster image (does not save)
# -------------------
def preview_roster_image(df, days, shift_hours, employee_colors, activity_colors_dict):
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
    ax.invert_yaxis()

    # Only show first and last hours
    start_hour = int(shift_hours[0].split(":")[0])
    end_hour = int(shift_hours[-1].split(":")[0])
    ax.set_yticks([start_hour, end_hour])
    ax.set_yticklabels([shift_hours[0], shift_hours[-1]])

    # Legend
    emp_patches = [mpatches.Patch(color=color, label=emp) for emp,color in employee_colors.items() if emp!="None"]
    act_patches = [mpatches.Patch(edgecolor=color, facecolor='none', label=act, linewidth=2)
                   for act,color in activity_colors_dict.items() if act!="None"]
    ax.legend(handles=emp_patches + act_patches, bbox_to_anchor=(1.05,1), loc='upper left')

    plt.tight_layout()
    st.pyplot(fig)

# -------------------
# Function to save roster CSV and image
# -------------------
def save_roster(df, days, shift_hours, employee_colors, activity_colors_dict, save_folder):
    # Save CSV
    date_str = datetime.now().strftime("%Y-%m-%d_%H%M")
    csv_path = os.path.join(save_folder, f"roster_{date_str}.csv")
    df.to_csv(csv_path, index=False)

    # Save image
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
    ax.invert_yaxis()

    # Only show first and last hours
    start_hour = int(shift_hours[0].split(":")[0])
    end_hour = int(shift_hours[-1].split(":")[0])
    ax.set_yticks([start_hour, end_hour])
    ax.set_yticklabels([shift_hours[0], shift_hours[-1]])

    # Legend
    emp_patches = [mpatches.Patch(color=color, label=emp) for emp,color in employee_colors.items() if emp!="None"]
    act_patches = [mpatches.Patch(edgecolor=color, facecolor='none', label=act, linewidth=2)
                   for act,color in activity_colors_dict.items() if act!="None"]
    ax.legend(handles=emp_patches + act_patches, bbox_to_anchor=(1.05,1), loc='upper left')

    plt.tight_layout()
    img_path = os.path.join(save_folder, f"roster_{date_str}.jpg")
    plt.savefig(img_path, dpi=300)
    st.success(f"Roster saved to {csv_path} and {img_path}")


# -------------------
# MAIN
# -------------------
# -------------------
# Default links
# -------------------
default_links = [
    "https://newdle.cern.ch/newdle/w5NzNRKR",
    "https://example.com/newdle2",
    "",  # placeholders for up to 4
    ""
]

# Store links in session state
if "newdle_links" not in st.session_state:
    st.session_state["newdle_links"] = default_links.copy()

# -------------------
# Display links horizontally
# -------------------
st.markdown("### Next Newdles:")
cols = st.columns(4)
for i, (col, link) in enumerate(zip(cols, st.session_state["newdle_links"])):
    if link.strip():
        title = get_newdle_title(link)
        col.markdown(f"[{title}]({link})")

st.markdown("### Roster Image")

# Get all saved roster images
jpg_files = [f for f in os.listdir(SAVE_FOLDER) if f.endswith(".jpg")]
jpg_files.sort(reverse=True)  # latest first

# Add a dropdown to select old images
selected_jpg = st.selectbox(
    "Select a roster image (latest first)",
    ["LATEST"] + jpg_files  # "LATEST" will be the most recent image
)

# Button to force refresh to latest image
if st.button("🖼️ Refresh Latest"):
    selected_jpg = "LATEST"

# Determine which image to show
if selected_jpg == "LATEST":
    if jpg_files:
        latest_jpg_path = os.path.join(SAVE_FOLDER, jpg_files[0])
        st.image(latest_jpg_path, caption=f"Latest roster image ({jpg_files[0]})", use_container_width=True)
    else:
        st.warning("No roster images found yet.")
else:
    st.image(os.path.join(SAVE_FOLDER, selected_jpg), caption=f"Roster image ({selected_jpg})", use_container_width=True)

# -------------------
# Load availability and roster data
# -------------------
availability_df = load_newest_csv(AVAILABILITY_FOLDER)
employees = sorted(availability_df['Name'].unique())
days = sorted(availability_df['Day'].unique())
shift_hours = sorted(availability_df['Hour'].unique())

# Colors
colors = plt.cm.tab10.colors
employee_colors = {emp: colors[i % len(colors)] for i, emp in enumerate(employees)}
activity_colors = plt.cm.Set2.colors
activity_colors_dict = {act: activity_colors[i % len(activity_colors)] if act != "None" else "gray"
                        for i, act in enumerate(activities)}

availability_map = map_availability(availability_df)
latest_roster_df = get_last_roster(AVAILABILITY_FOLDER)


# -------------------
# Streamlit ICS download section
# -------------------
latest_csv = get_latest_roster_csv(SAVE_FOLDER)
if latest_csv is None:
    st.warning("No roster CSVs found to generate ICS.")
else:
    df = pd.read_csv(latest_csv)
    employees = sorted(set(df['Employee1']).union(df['Employee2'], df['Employee3'], df['Employee4']))
    employee_selected = st.selectbox("Select your name", ["None"] + employees)
    
    if employee_selected != "None":
        calendar = generate_employee_ics_from_csv(latest_csv, employee_selected)
        st.download_button(
            label=f"Download ICS for {employee_selected}",
            data=str(calendar),
            file_name=f"{employee_selected}_shifts.ics",
            mime="text/calendar"
        )

# -------------------
# PASSWORD PROTECTION
# -------------------

st.subheader("Enter Password to Enable Editor & Actions")
entered_password = st.text_input("Password", type="password")
safe_password = html.escape(entered_password)  # Extra safety if ever rendered
    
if safe_password == PASSWORD:
    
        
    roster_data = build_roster_editor(days, shift_hours, employees, activities, availability_map, latest_roster_df)
    st.subheader("Actions")
    # Row of first three buttons
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📤 Upload & Process CSV"):
            availability_df = upload_and_process_newdle_csv()
            if availability_df is not None:
                st.experimental_rerun()

    with col2:
        if st.button("🖼️ Update Image"):
            show_latest_image(SAVE_FOLDER)

    with col3:
        if st.button("📢 Send Notification"):
            send_schedule_notification()

            
    st.markdown("### Update Next Newdle Links (up to 4)")
    for i in range(4):
        new_link = st.text_input(
            f"Link {i+1}",
            value=st.session_state["newdle_links"][i],
            key=f"link_input_{i}"
        )
        st.session_state["newdle_links"][i] = new_link.strip()

    if st.button("💾 Save Links"):
        st.success("Newdle links updated!")
            

    if st.button("Save and Plot Roster"):
        save_and_plot(roster_data, days, shift_hours, employee_colors, activity_colors_dict, SAVE_FOLDER)
            
    if st.button("🖼️ Show / Preview Roster"):
        preview_roster_image(latest_roster_df, days, shift_hours, employee_colors, activity_colors_dict)

    if st.button("💾 Save Roster (CSV & JPG)"):
        save_roster(latest_roster_df, days, shift_hours, employee_colors, activity_colors_dict, SAVE_FOLDER)

else:
    st.warning("Enter the correct password to enable actions.")
