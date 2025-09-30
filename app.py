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
import glob


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
PASSWORD = "123"  # Replace with your desired password
activities = ["None", "Cabling ETH", "Airex Foiling", "Airex Modif.","Airex Gluing", "Beam Precal.", "Grounding Strips"]

# -------------------
# Utility functions
# -------------------
def process_newdle_csv(file_path, save_folder):
    """
    Process a Newdle CSV export into a standard availability DataFrame
    and save it with a date-stamped filename.
    """
    df = pd.read_csv(file_path)
    
    # Identify time slot columns (exclude 'Participant name' and 'Comment')
    time_slots = [col for col in df.columns if col not in ['Participant name', 'Comment']]

    # Extract rows
    rows = []
    for _, row in df.iterrows():
        name = str(row.get('Participant name', 'Unknown')).strip()
        for ts in time_slots:
            try:
                day, hour = ts.split("T")
            except Exception:
                continue  # skip malformed column names
            availability = str(row[ts]).strip().lower()
            if availability not in ['available', 'unavailable']:
                availability = 'unavailable'
            rows.append([day, hour, name, availability])

    availability_df = pd.DataFrame(rows, columns=['Day', 'Hour', 'Name', 'Availability'])

    # Save with current date
    date_str = datetime.now().strftime("%Y-%m-%d_%H%M")
    save_path = os.path.join(save_folder, f"availability_{date_str}.csv")
    availability_df.to_csv(save_path, index=False)
    
    return availability_df, save_path
def upload_and_save_newdle_csv():
    """
    Streamlit uploader to save a new CSV into the Newdles folder.
    """
    st.subheader("Upload a Newdle CSV")

    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
    if uploaded_file is not None:
        try:
            # Read CSV to check it's valid
            df = pd.read_csv(uploaded_file)
            # Save to folder with timestamp to avoid overwriting
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = os.path.join(NEWLDES_FOLDER, f"newdle_{timestamp}.csv")
            df.to_csv(save_path, index=False)
            st.success(f"CSV saved successfully to {save_path}")
            return df  # return dataframe in case you want to use it immediately
        except Exception as e:
            st.error(f"Error reading or saving CSV: {e}")
    return None
def safe_index(options, value):
    try:
        return options.index(value)
    except ValueError:
        return 0  # fallback to "None"

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
    csv_files = glob.glob(os.path.join(folder, "*.csv"))  # ✅ use glob.glob
    if csv_files:
        return max(csv_files, key=os.path.getmtime)
    return None

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



def get_latest_roster_csv(save_folder: str) -> str | None:
    """Return the path of the latest CSV in the folder, or None if none exist."""
    csv_files = [f for f in os.listdir(save_folder) if f.endswith(".csv")]
    if not csv_files:
        return None
    latest_csv = max(csv_files, key=lambda f: os.path.getmtime(os.path.join(save_folder, f)))
    return os.path.join(save_folder, latest_csv)


def extract_employees(df: pd.DataFrame, employee_cols=None) -> list[str]:
    """Return a sorted list of unique employee names from the given DataFrame."""
    if employee_cols is None:
        employee_cols = ['Employee1', 'Employee2', 'Employee3', 'Employee4']
    
    all_employees = set()
    for col in employee_cols:
        if col in df.columns:
            all_employees.update(df[col].dropna().astype(str))
    return sorted(all_employees)


def select_employee(employees: list[str]) -> str | None:
    """Display a Streamlit selectbox to choose an employee."""
    employee_selected = st.selectbox("Select your name", ["None"] + employees)
    return None if employee_selected == "None" else employee_selected


def download_ics(latest_csv: str, employee: str):
    """Generate ICS for an employee and add a Streamlit download button."""
    calendar = generate_employee_ics_from_csv(latest_csv, employee)
    st.download_button(
        label=f"Download ICS for {employee}",
        data=str(calendar),
        file_name=f"{employee}_shifts.ics",
        mime="text/calendar"
    )

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
def show_latest_image(folder: str):
    jpg_files = [f for f in os.listdir(folder) if f.endswith(".jpg")]
    if jpg_files:
        latest_jpg = max(jpg_files, key=lambda f: os.path.getmtime(os.path.join(folder, f)))
        st.image(os.path.join(folder, latest_jpg), caption=f"Latest roster image ({latest_jpg})", use_container_width=True)
    else:
        st.warning("No roster images found yet.")

# -------------------
# CSV Loading
# -------------------
def get_last_roster(folder: str) -> pd.DataFrame:
    """Load the most recent roster CSV, ensuring all fields are strings."""
    roster_files = [f for f in os.listdir(folder) if f.endswith(".csv")]
    if roster_files:
        latest_roster = max(roster_files, key=lambda f: os.path.getmtime(os.path.join(folder, f)))
        st.success(f"Prefilling from last roster: {latest_roster}")
        df = pd.read_csv(os.path.join(folder, latest_roster), dtype=str).fillna("None")
        return df
    st.warning("No previous roster found, starting empty.")
    return None

# -------------------
# Availability Mapping
# -------------------
def map_availability(df: pd.DataFrame) -> dict:
    """Map availability from DataFrame to a nested dict: day -> hour -> employees."""
    availability_map = {day:{} for day in df['Day'].unique()}
    for _, row in df.iterrows():
        name = str(row.get('Name', 'None'))
        day = str(row.get('Day', ''))
        hour = str(row.get('Hour', ''))
        avail = str(row.get('Availability', 'None')).strip().lower()
        if avail == "available":
            availability_map.setdefault(day, {}).setdefault(hour, []).append(name)
    return availability_map
# -------------------
# Build Roster Editor
# -------------------
def build_roster_editor(days, shift_hours, activities, SAVE_FOLDER, AVAILABILITY_FOLDER):
    """
    Streamlit roster editor:
    - Default: all fields "None"
    - Two buttons to prefill from last roster or availability
    - Dropdowns to select older CSVs
    - Highlights prefilled values in light green *below* their selectbox
    - Layout: 2 rows of assignments per hour
    """
    st.header("Roster Editor")

    # --- Initialize roster_data ---
    if "roster_data" not in st.session_state:
        st.session_state["roster_data"] = [
            {
                "Day": day, "Hour": hour,
                **{f"Emp{i}": "None" for i in range(1, 9)},
                **{f"Act{j}": "None" for j in range(1, 5)},
            }
            for day in days for hour in shift_hours
        ]

    # --- Prefill buttons and dropdowns ---
    col1, col2 = st.columns(2)

    roster_files = [f for f in os.listdir(SAVE_FOLDER) if f.endswith(".csv")]
    roster_files.sort(reverse=True)
    selected_roster_csv = st.selectbox("Select roster CSV to prefill", ["LATEST"] + roster_files)

    with col1:
        if st.button("📄 Prefill from Selected Roster"):
            if selected_roster_csv == "LATEST" and roster_files:
                csv_path = os.path.join(SAVE_FOLDER, roster_files[0])
            elif selected_roster_csv != "LATEST":
                csv_path = os.path.join(SAVE_FOLDER, selected_roster_csv)
            else:
                csv_path = None

            if csv_path:
                latest_roster_df = pd.read_csv(csv_path, dtype=str).fillna("None")
                for row in st.session_state["roster_data"]:
                    match = latest_roster_df[
                        (latest_roster_df.get("Day", "") == row["Day"]) &
                        (latest_roster_df.get("Hour", "") == row["Hour"])
                    ]
                    if not match.empty:
                        for e in range(1, 9):
                            row[f"Emp{e}"] = match.iloc[0].get(f"Emp{e}", "None") or "None"
                        for a in range(1, 5):
                            row[f"Act{a}"] = match.iloc[0].get(f"Act{a}", "None") or "None"
            st.session_state["prefill_trigger"] = not st.session_state.get("prefill_trigger", False)

    avail_files = [f for f in os.listdir(AVAILABILITY_FOLDER) if f.endswith(".csv")]
    avail_files.sort(reverse=True)
    selected_avail_csv = st.selectbox("Select availability CSV to prefill", ["LATEST"] + avail_files)

    with col2:
        if st.button("📅 Prefill from Selected Availability"):
            if selected_avail_csv == "LATEST" and avail_files:
                csv_path = os.path.join(AVAILABILITY_FOLDER, avail_files[0])
            elif selected_avail_csv != "LATEST":
                csv_path = os.path.join(AVAILABILITY_FOLDER, selected_avail_csv)
            else:
                csv_path = None

            if csv_path:
                availability_df = pd.read_csv(csv_path, dtype=str).fillna("None")
                for row in st.session_state["roster_data"]:
                    available_emps = availability_df[
                        (availability_df.get("Day", "") == row["Day"]) &
                        (availability_df.get("Hour", "") == row["Hour"]) &
                        (availability_df.get("Availability", "").str.lower() == "available")
                    ]["Name"].tolist()
                    for e in range(1, 9):
                        row[f"Emp{e}"] = available_emps[e-1] if len(available_emps) >= e else "None"
            st.session_state["prefill_trigger"] = not st.session_state.get("prefill_trigger", False)

    # --- Build editor UI ---
    employees = sorted(set([r[e] for r in st.session_state["roster_data"] for e in [f"Emp{i}" for i in range(1, 9)]]))
    employee_options = ["None"] + employees

    for day in days:
        st.subheader(day)
        for hour in shift_hours:
            row_data = next(r for r in st.session_state["roster_data"] if r["Day"] == day and r["Hour"] == hour)

            st.markdown(f"**Hour: {hour}**")

            # --- Row 1 ---
            row1_cols = st.columns(6)
            for i, field in enumerate(["Emp1", "Emp2", "Act1", "Emp3", "Emp4", "Act2"]):
                if "Emp" in field:
                    options = employee_options
                    idx = employee_options.index(row_data[field])
                else:
                    options = activities
                    idx = activities.index(row_data[field]) if row_data[field] in activities else 0

                row_data[field] = row1_cols[i].selectbox(field, options, index=idx, key=f"{day}_{hour}_{field}")
                if row_data[field] != "None":  # highlight below selectbox
                    row1_cols[i].markdown(
                        f'<div style="background-color:#d0f0c0; border-radius:4px; padding:2px; text-align:center">{row_data[field]}</div>',
                        unsafe_allow_html=True
                    )

            # --- Row 2 ---
            row2_cols = st.columns(6)
            for i, field in enumerate(["Emp5", "Emp6", "Act3", "Emp7", "Emp8", "Act4"]):
                if "Emp" in field:
                    options = employee_options
                    idx = employee_options.index(row_data[field])
                else:
                    options = activities
                    idx = activities.index(row_data[field]) if row_data[field] in activities else 0

                row_data[field] = row2_cols[i].selectbox(field, options, index=idx, key=f"{day}_{hour}_{field}")
                if row_data[field] != "None":  # highlight below selectbox
                    row2_cols[i].markdown(
                        f'<div style="background-color:#d0f0c0; border-radius:4px; padding:2px; text-align:center">{row_data[field]}</div>',
                        unsafe_allow_html=True
                    )

    return st.session_state["roster_data"]


def save_and_plot(days, shift_hours, employee_colors, activity_colors_dict, save_folder):
    """
    Save and plot the roster using the current values from st.session_state.
    Supports up to Emp1–Emp8 and Act1–Act4.
    Each 2 employees are surrounded by a rectangle of the corresponding activity color.
    """
    roster_data = st.session_state.get("roster_data", [])

    if not roster_data:
        st.warning("Roster is empty, nothing to save.")
        return

    df = pd.DataFrame(roster_data, columns=["Day", "Hour"] +
                      [f"Emp{i}" for i in range(1, 9)] +
                      [f"Act{j}" for j in range(1, 5)])

    date_str = datetime.now().strftime("%Y-%m-%d_%H%M")
    csv_path = os.path.join(save_folder, f"roster_{date_str}.csv")
    df.to_csv(csv_path, index=False)

    fig, ax = plt.subplots(figsize=(12, 6))
    bar_width = 0.5
    day_positions = range(len(days))

    for day_idx, day in enumerate(days):
        for hour_idx, hour in enumerate(shift_hours):
            row = df[(df["Day"] == day) & (df["Hour"] == hour)]
            if row.empty:
                continue
            row = row.iloc[0]

            start_hour = int(hour.split(":")[0])
            height = 0.25

            # Employee–activity pairs (two per activity)
            emp_act_pairs = [
                (row.Emp1, row.Act1),
                (row.Emp2, row.Act1),
                (row.Emp3, row.Act2),
                (row.Emp4, row.Act2),
                (row.Emp5, row.Act3),
                (row.Emp6, row.Act3),
                (row.Emp7, row.Act4),
                (row.Emp8, row.Act4),
            ]

            # Plot employees
            for i, (emp, act) in enumerate(emp_act_pairs):
                if emp is None or emp == "None":
                    bar_color = "white"
                    text_color = "black"
                    display_emp = ""
                else:
                    bar_color = employee_colors.get(emp, 'gray')
                    text_color = 'white'
                    display_emp = emp

                ax.bar(day_idx, height, bottom=start_hour + i * height, width=bar_width,
                       color=bar_color, edgecolor='black')
                ax.text(day_idx, start_hour + (i + 0.5) * height,
                        f"{display_emp}\n{act if act != 'None' else ''}",
                        ha='center', va='center', color=text_color, fontsize=7)

            # Surround pairs with activity-colored rectangles
            for pair_idx, act_col in enumerate([row.Act1, row.Act2, row.Act3, row.Act4]):
                if act_col and act_col != "None":
                    act_color = activity_colors_dict.get(act_col, "black")
                    base_y = start_hour + pair_idx * 2 * height
                    rect_height = 2 * height
                    rect = plt.Rectangle(
                        (day_idx - bar_width/2, base_y),
                        bar_width, rect_height,
                        fill=False, edgecolor=act_color, linewidth=2
                    )
                    ax.add_patch(rect)

    ax.set_xticks(list(day_positions))
    ax.set_xticklabels(days)
    ax.set_ylabel("Hour")
    ax.set_title("Weekly Schedule")
    ax.grid(True, axis='y', linestyle='--', alpha=0.5)
    ax.invert_yaxis()

    start_hour = int(shift_hours[0].split(":")[0])
    end_hour = int(shift_hours[-1].split(":")[0])
    ax.set_yticks([start_hour, end_hour])
    ax.set_yticklabels([shift_hours[0], shift_hours[-1]])

    import matplotlib.patches as mpatches
    emp_patches = [mpatches.Patch(color=color, label=emp)
                   for emp, color in employee_colors.items() if emp != "None"]
    act_patches = [mpatches.Patch(edgecolor=color, facecolor='none', label=act, linewidth=2)
                   for act, color in activity_colors_dict.items() if act != "None"]
    ax.legend(handles=emp_patches + act_patches, bbox_to_anchor=(1.05, 1), loc='upper left')

    plt.tight_layout()
    img_path = os.path.join(save_folder, f"roster_{date_str}.jpg")
    plt.savefig(img_path, dpi=300)
    st.pyplot(fig)
    st.success(f"Roster saved to {csv_path} and {img_path}")


def preview_roster(days, shift_hours, employee_colors, activity_colors_dict):
    """
    Preview the current roster in a plot using session_state.
    Supports up to Emp1–Emp8 and Act1–Act4.
    Each 2 employees are surrounded by a rectangle of the corresponding activity color.
    """
    roster_data = st.session_state.get("roster_data", [])
    if not roster_data:
        st.warning("Roster is empty, nothing to preview.")
        return

    df = pd.DataFrame(roster_data, columns=["Day", "Hour"] +
                      [f"Emp{i}" for i in range(1, 9)] +
                      [f"Act{j}" for j in range(1, 5)])

    fig, ax = plt.subplots(figsize=(12, 6))
    bar_width = 0.5
    day_positions = range(len(days))

    for day_idx, day in enumerate(days):
        for hour_idx, hour in enumerate(shift_hours):
            row = df[(df["Day"] == day) & (df["Hour"] == hour)]
            if row.empty:
                continue
            row = row.iloc[0]

            start_hour = int(hour.split(":")[0])
            height = 0.25

            emp_act_pairs = [
                (row.Emp1, row.Act1),
                (row.Emp2, row.Act1),
                (row.Emp3, row.Act2),
                (row.Emp4, row.Act2),
                (row.Emp5, row.Act3),
                (row.Emp6, row.Act3),
                (row.Emp7, row.Act4),
                (row.Emp8, row.Act4),
            ]

            for i, (emp, act) in enumerate(emp_act_pairs):
                if emp is None or emp == "None":
                    bar_color = "white"
                    text_color = "black"
                    display_emp = ""
                else:
                    bar_color = employee_colors.get(emp, 'gray')
                    text_color = 'white'
                    display_emp = emp

                ax.bar(day_idx, height, bottom=start_hour + i * height, width=bar_width,
                       color=bar_color, edgecolor='black')
                ax.text(day_idx, start_hour + (i + 0.5) * height,
                        f"{display_emp}\n{act if act != 'None' else ''}",
                        ha='center', va='center', color=text_color, fontsize=7)

            # Surround pairs with activity-colored rectangles
            for pair_idx, act_col in enumerate([row.Act1, row.Act2, row.Act3, row.Act4]):
                if act_col and act_col != "None":
                    act_color = activity_colors_dict.get(act_col, "black")
                    base_y = start_hour + pair_idx * 2 * height
                    rect_height = 2 * height
                    rect = plt.Rectangle(
                        (day_idx - bar_width/2, base_y),
                        bar_width, rect_height,
                        fill=False, edgecolor=act_color, linewidth=2
                    )
                    ax.add_patch(rect)

    ax.set_xticks(list(day_positions))
    ax.set_xticklabels(days)
    ax.set_ylabel("Hour")
    ax.set_title("Roster Preview")
    ax.grid(True, axis='y', linestyle='--', alpha=0.5)
    ax.invert_yaxis()

    start_hour = int(shift_hours[0].split(":")[0])
    end_hour = int(shift_hours[-1].split(":")[0])
    ax.set_yticks([start_hour, end_hour])
    ax.set_yticklabels([shift_hours[0], shift_hours[-1]])

    import matplotlib.patches as mpatches
    emp_patches = [mpatches.Patch(color=color, label=emp)
                   for emp, color in employee_colors.items() if emp != "None"]
    act_patches = [mpatches.Patch(edgecolor=color, facecolor='none', label=act, linewidth=2)
                   for act, color in activity_colors_dict.items() if act != "None"]
    ax.legend(handles=emp_patches + act_patches, bbox_to_anchor=(1.05, 1), loc='upper left')

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

def show_notes_box(filename="notes.txt"):
    """Display the contents of a txt file in a non-editable text box."""
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = "No notes available (file not found)."

    st.subheader("Notes")
    st.text_area("File contents", content, height=300, disabled=True)
    # Alternative (more compact look):
    # st.code(content, language=None)

import html

def sanitize_text(raw_text: str) -> str:
    # 1. Escape HTML/JS
    text = html.escape(raw_text)
    # 2. Remove unprintable/control characters
    text = ''.join(ch for ch in text if ch.isprintable() or ch in '\n\t')
    # 3. Optionally, limit length
    return text[:10000]  # prevent insanely long input

def editable_notes_box(filename="notes.txt"):
    """Show and edit the contents of a txt file safely in the Streamlit app."""
    
    # Load file contents
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = ""

    st.subheader("Notes Editor")

    # Editable text box (plain text)
    edited_content = st.text_area("Edit notes", content, height=300)

    # Save button
    if st.button("💾 Save Notes"):
        safe_content = sanitize_text(edited_content)  # sanitize input
        with open(filename, "w", encoding="utf-8") as f:
            f.write(safe_content)
        st.success("Notes saved successfully!")
        st.experimental_rerun()  # refresh the app
    
# -------------------
# MAIN
# -------------------

# -------------------
# Default links
# -------------------
st.set_page_config(layout="wide")  # expands app to full width

default_links = [
    "https://newdle.cern.ch/newdle/w5NzNRKR",
    "https://example.com/newdle2",
    "", "",  # placeholders for up to 4
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

# -------------------
# Roster Image
# -------------------
st.markdown("### Roster Image")
jpg_files = [f for f in os.listdir(SAVE_FOLDER) if f.endswith(".jpg")]
jpg_files.sort(reverse=True)
selected_jpg = st.selectbox("Select a roster image (latest first)", ["LATEST"] + jpg_files)

if st.button("🖼️ Refresh Latest"):
    selected_jpg = "LATEST"

if selected_jpg == "LATEST":
    if jpg_files:
        st.image(os.path.join(SAVE_FOLDER, jpg_files[0]), caption=f"Latest roster image ({jpg_files[0]})", use_container_width=True)
    else:
        st.warning("No roster images found yet.")
else:
    st.image(os.path.join(SAVE_FOLDER, selected_jpg), caption=f"Roster image ({selected_jpg})", use_container_width=True)

# -------------------
# Load availability data (for ICS download)
# -------------------
availability_df = load_newest_csv(AVAILABILITY_FOLDER)
employees = sorted(availability_df['Name'].unique())
days = sorted(availability_df['Day'].unique())
shift_hours = sorted(availability_df['Hour'].unique())
latest_csv = get_latest_roster_csv(SAVE_FOLDER)
df = pd.read_csv(latest_csv)
employee_selected = select_employee(extract_employees(df))
if employee_selected:
    download_ics(latest_csv, employee_selected)

show_notes_box("myfile.txt")
    
# -------------------
# PASSWORD PROTECTION
# -------------------
st.subheader("Enter Password to Enable Editor & Actions")
entered_password = st.text_input("Password", type="password")
safe_password = html.escape(entered_password)

if safe_password == PASSWORD:
    # -------------------
    # Roster Editor
    # -------------------
    roster_data = build_roster_editor(days, shift_hours, activities, SAVE_FOLDER, AVAILABILITY_FOLDER)

    # -------------------
    # Colors for plotting
    # -------------------
    colors = plt.cm.tab10.colors
    employee_list = sorted(set([r[e] for r in roster_data for e in ["Emp1","Emp2","Emp3","Emp4"]]))
    employee_colors = {emp: colors[i % len(colors)] for i, emp in enumerate(employee_list)}
    activity_colors = plt.cm.Set2.colors
    activity_colors_dict = {act: activity_colors[i % len(activity_colors)] if act != "None" else "gray" for i, act in enumerate(activities)}

    # -------------------
    # Actions
    # -------------------
    st.subheader("Pre-processing")
    if st.button("📤 Upload & Save Newdle CSV"):
        uploaded_df = upload_and_save_newdle_csv()
        if uploaded_df is not None:
            st.write("Preview of uploaded CSV:")
            st.dataframe(uploaded_df)
    
    # Find all CSVs in the folder
    #csv_files = glob(os.path.join(NEWDLE_FOLDER, "*.csv"))
    csv_files = glob.glob(os.path.join(NEWDLE_FOLDER, "*.csv"))  # works

    csv_files.sort(key=os.path.getmtime, reverse=True)  # newest first

    if not csv_files:
        st.warning(f"No CSV files found in folder '{NEWDLE_FOLDER}'")
    else:
        st.subheader("Select a Newdle CSV to process")
        selected_csv = st.selectbox("Choose CSV", csv_files, format_func=lambda x: os.path.basename(x))

        if st.button("📤 Process Selected CSV"):
            try:
                availability_df, save_path = process_newdle_csv(selected_csv, AVAILABILITY_FOLDER)
                st.success(f"Processed successfully! Saved to `{save_path}`")
                st.dataframe(availability_df)
            except Exception as e:
                st.error(f"Error processing CSV: {e}")
    
    # -------------------
    # Update Next Newdle Links
    # -------------------
    st.markdown("### Update Next Newdle Links (up to 4)")
    for i in range(4):
        new_link = st.text_input(f"Link {i+1}", value=st.session_state["newdle_links"][i], key=f"link_input_{i}")
        st.session_state["newdle_links"][i] = new_link.strip()

    if st.button("💾 Save Links"):
        st.success("Newdle links updated!")
    
    
    st.subheader("Actions")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📤 Upload & Process CSV"):
            availability_df = upload_and_process_newdle_csv()
            if availability_df is not None:
                st.experimental_rerun()
    #with col2:
    #    if st.button("🖼️ Update Image"):
    #        show_latest_image(SAVE_FOLDER)
    with col3:
        if st.button("📢 Send Notification"):
            send_schedule_notification()

    # --- Button in main app ---
    if st.button("🖼️ Preview Roster"):
        preview_roster(days, shift_hours, employee_colors, activity_colors_dict)
    # -------------------
    # Save and Plot Roster
    # -------------------
    if st.button("Save and Plot Roster"):
        save_and_plot(days, shift_hours, employee_colors, activity_colors_dict, SAVE_FOLDER)

    editable_notes_box("myfile.txt")


else:
    st.warning("Enter the correct password to enable actions.")

