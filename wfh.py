import subprocess
import json
import os
from pathlib import Path
from datetime import datetime

# ===== Configuration =====
JSON_FILE = os.path.expanduser("~/wifi_connection_log.json")
PLIST_PATH = os.path.expanduser("~/Library/LaunchAgents/com.user.wifilogger.plist")
PYTHON_PATH = "/usr/bin/python3"
SCRIPT_PATH = os.path.abspath(__file__)
OFFICE_SSIDS = {"ACT_BB", "Airtel_ajan_6120"}  # Update with your office SSIDs
EXPECTED_OFFICE_DAYS = 12

# ===== Load/Save JSON Log =====
def load_existing_log():
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, "r") as f:
            return json.load(f)
    return {}

def save_log(log):
    with open(JSON_FILE, "w") as f:
        json.dump(log, f, indent=2)

# ===== Parse Wi-Fi Logs from System =====
def get_wifi_connections_last_2h():
    command = """
    log show --style syslog --predicate 'process == "airportd"' --last 2d | \
    grep -i "Successfully associated to" | \
    sed -E 's/.*([0-9]{4}-[0-9]{2}-[0-9]{2}).*Successfully associated to Wi-Fi network (.*) on interface.*/\\1 \\2/' | \
    sort | uniq
    """
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(" Error from log command:", result.stderr.strip())
            return []
        return result.stdout.strip().split("\n")
    except Exception as e:
        print("Exception while running command:", str(e))
        return []

# ===== Update Log with New Entries =====
def update_wifi_log():
    wifi_logs = get_wifi_connections_last_2h()
    if not wifi_logs:
        return

    log_data = load_existing_log()

    for line in wifi_logs:
        parts = line.strip().split(maxsplit=1)
        if len(parts) == 2:
            date, ssid = parts
            if date not in log_data:
                log_data[date] = []
            if ssid not in log_data[date]:
                log_data[date].append(ssid)

    save_log(log_data)
    print(f"Wi-Fi log updated at {JSON_FILE}")

# ===== Count Office Visit Days =====
def count_office_days(log):
    current_month = datetime.today().strftime("%Y-%m")
    return sum(
        1 for date, ssids in log.items()
        if date.startswith(current_month) and any(ssid in OFFICE_SSIDS for ssid in ssids)
    )

# ===== Add Reminder to macOS =====
def add_reminder_to_macos(attended_days, remaining_days):
    title = f"Attended office for {attended_days} day(s) this month – {remaining_days} more to go!"

    clear_script = """
    tell application "Reminders"
        set theList to list "Reminders"
        repeat with r in (get reminders of theList)
            if name of r starts with "Attended office for" then
                delete r
            end if
        end repeat
    end tell
    """
    subprocess.run(["osascript", "-e", clear_script])

    add_script = f'''
    tell application "Reminders"
        make new reminder with properties {{name:"{title}"}}
    end tell
    '''
    subprocess.run(["osascript", "-e", add_script])
    print(f" Reminder added: {title}")

# ===== Show Summary & Update Reminder =====
def print_office_visit_summary():
    log = load_existing_log()
    office_days = count_office_days(log)
    remaining = max(EXPECTED_OFFICE_DAYS - office_days, 0)
    print(f"Office visits this month: {office_days} day(s)")
    print(f"Remaining to reach {EXPECTED_OFFICE_DAYS}: {remaining} day(s)")
    add_reminder_to_macos(office_days, remaining)

# ===== Create & Load launchd plist (for automation) =====
def create_and_load_launchd_plist():
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
"http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.wifilogger</string>
    <key>ProgramArguments</key>
    <array>
        <string>{PYTHON_PATH}</string>
        <string>{SCRIPT_PATH}</string>
    </array>
    <key>StartInterval</key>
    <integer>7200</integer>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
"""
    os.makedirs(os.path.dirname(PLIST_PATH), exist_ok=True)
    with open(PLIST_PATH, "w") as f:
        f.write(plist_content)

    subprocess.run(["launchctl", "unload", PLIST_PATH], stderr=subprocess.DEVNULL)
    subprocess.run(["launchctl", "load", PLIST_PATH])
    print(f" launchd loaded: {PLIST_PATH} (runs every 2 hours)")

# ===== Main Entry Point =====
if __name__ == "__main__":
    update_wifi_log()
    print_office_visit_summary()
    create_and_load_launchd_plist()
