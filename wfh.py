import os
from pathlib import Path
import subprocess

home = str(Path.home())
wifi_logger_path = os.path.join(home, "wifi_logger_1.py")
plist_path = os.path.join(home, "Library/LaunchAgents/com.user.wifilogger.plist")

# Create wifi_logger.py
wifi_logger_content = '''\
import subprocess
import datetime
import os
import json

def get_wifi_info():
    ssid = "Unknown"
    bssid = "Unavailable"
    try:
        result = subprocess.run(
            ["networksetup", "-getairportnetwork", "en0"],
            capture_output=True, text=True
        )
        if "You are not associated" in result.stdout:
            ssid = "Not Connected"
        else:
            ssid = result.stdout.strip().split(": ")[1]

        bssid_result = subprocess.run(
            ["/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport", "-I"],
            capture_output=True, text=True
        )
        for line in bssid_result.stdout.split("\\n"):
            if " BSSID:" in line:
                bssid = line.strip().split(": ")[1]
    except Exception as e:
        ssid = bssid = f"Error: {e}"
    return ssid, bssid

def log_wifi_info():
    ssid, bssid = get_wifi_info()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = {
        "timestamp": timestamp,
        "ssid": ssid,
        "bssid": bssid
    }

    log_path = os.path.expanduser("~/wifi_log_1.json")
    if os.path.exists(log_path):
        try:
            with open(log_path, "r") as f:
                logs = json.load(f)
        except json.JSONDecodeError:
            logs = []
    else:
        logs = []

    logs.append(log_entry)
    with open(log_path, "w") as f:
        json.dump(logs, f, indent=2)

def count_days_connected_to_ssids(log_path, ssid_names):
    if not os.path.exists(log_path):
        return 0

    with open(log_path, "r") as f:
        try:
            logs = json.load(f)
        except json.JSONDecodeError:
            return 0

    current_month = datetime.datetime.now().strftime("%Y-%m")
    connected_days = set()

    for entry in logs:
        ssid = entry.get("ssid")
        if ssid in ssid_names:
            try:
                ts = datetime.datetime.strptime(entry["timestamp"], "%Y-%m-%d %H:%M:%S")
                if ts.strftime("%Y-%m") == current_month:
                    connected_days.add(ts.date())
            except Exception:
                continue

    return len(connected_days)

def delete_old_reminders(keyword="Attended office for"):
    script = f"""
    tell application "Reminders"
        set theList to reminders of default list
        repeat with r in theList
            if name of r starts with "{keyword}" then
                delete r
            end if
        end repeat
    end tell
    """
    subprocess.run(["osascript", "-e", script])

def create_mac_reminder(title, note=""):
    script = f"""
    tell application "Reminders"
        set newReminder to make new reminder with properties {{name:"{title}", body:"{note}"}}
    end tell
    """
    subprocess.run(["osascript", "-e", script])

if __name__ == "__main__":
    log_wifi_info()
    ssid_names = {"wifi_name1", "wifi_name2"}
    log_file_path = os.path.expanduser("~/wifi_log_1.json")
    days = count_days_connected_to_ssids(log_file_path, ssid_names)
    delete_old_reminders("Attended office for")
    if days > 0:
        title = title = f"Attended office for {days} day(s) this month - Remaining {12 - days} to go!!!"
        note = "Check your PTO's and SL's."
        create_mac_reminder(title, note)
'''

try:
    with open(wifi_logger_path, "w") as f:
        f.write(wifi_logger_content)
    os.chmod(wifi_logger_path, 0o755)
    print(f"Created {wifi_logger_path}")
except Exception as e:
    print(f"Failed to create wifi_logger.py: {e}")



# Create LaunchAgent plist
plist_content = f'''\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" 
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.wifilogger</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>{wifi_logger_path}</string>
    </array>

    <key>StartInterval</key>
    <integer>300</integer> <!-- Every 2 hours -->

    <key>RunAtLoad</key>
    <true/>

    <key>StandardOutPath</key>
    <string>/tmp/wifilogger.out</string>
    <key>StandardErrorPath</key>
    <string>/tmp/wifilogger.err</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/bin:/bin:/usr/sbin:/sbin:/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources</string>
    </dict>
</dict>
</plist>
'''

os.makedirs(os.path.dirname(plist_path), exist_ok=True)
with open(plist_path, "w") as f:
    f.write(plist_content)
print(f"Created LaunchAgent at {plist_path}")

# Load into launchd
subprocess.run(["launchctl", "unload", plist_path], stderr=subprocess.DEVNULL)
subprocess.run(["launchctl", "load", plist_path])
print(" Loaded LaunchAgent — Wi-Fi logger will now run every 2 hours.")
