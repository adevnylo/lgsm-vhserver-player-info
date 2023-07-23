import os
import sys
import json
import time
import subprocess
import requests
import signal
from datetime import datetime

# Function to create and activate the virtual environment
def create_virtualenv():
    try:
        subprocess.check_call(["python3", "-m", "venv", "venv"])
    except subprocess.CalledProcessError as e:
        print(f"Failed to create virtual environment: {e}")
        sys.exit(1)

# Function to activate the virtual environment
def activate_virtualenv():
    activate_command = os.path.join("venv", "bin", "activate")
    if os.path.exists(activate_command):
        subprocess.Popen(f"source {activate_command}", shell=True, executable="/bin/bash")

# Function to read the log file and extract player info
def process_log_file(log_file, api_key):
    # Read the last check time from last_check_time.json
    last_check_time = read_last_check_time()

    # If last_check_time is None, set it to the current time
    if last_check_time is None:
        last_check_time = datetime.now()
        
    # Check if player_info.json exists and load its content
    if os.path.exists("player_info.json") and os.path.getsize("player_info.json") > 0:
        with open("player_info.json", "r") as f:
            player_info_data = json.load(f)
    else:
        player_info_data = []

    # Read the log file and process player info
    with open(log_file, "r") as f:
        lines = f.readlines()

        # Initialize variables to store player info
        player_steamID = None
        player_name = None
        player_steam_name = None

        # Iterate through each line in the log file
        for line in lines:
            # Check if the line contains "received local Platform ID Steam_"
            if "received local Platform ID Steam_" in line:
                player_steamID = line.split("received local Platform ID Steam_")[1][:17]

            # Check if the line contains "Got character ZDOID from"
            elif "Got character ZDOID from" in line:
                player_name = line.split("Got character ZDOID from ")[1].split(" :")[0]

                # Use the Steam API to get the Steam nickname
                player_steam_name = get_steam_nickname(player_steamID, api_key)

                # Check if the player_steamID is already processed
                if not is_steamID_processed(player_steamID, player_info_data):
                    # Create a dictionary with player info and append it to player_info_data
                    player_info = {
                        "player_serial": len(player_info_data) + 1,
                        "player_name": player_name,
                        "player_steamID": player_steamID,
                        "player_steam_name": player_steam_name
                    }
                    player_info_data.append(player_info)

                    # Print the player info
                    print_player_info(player_info)

                # If the player_steamID is already processed and the player_name is different, add it as a new entry
                elif player_steam_name != get_steam_name_for_steamID(player_steamID, player_info_data):
                    player_info_data.append({
                        "player_serial": len(player_info_data) + 1,
                        "player_name": f"{player_name}_{len(player_info_data) + 1}",
                        "player_steamID": player_steamID,
                        "player_steam_name": player_steam_name
                    })
                    print(f"Player {player_steamID} already exists with a different name. Adding new entry.")

            # Check if it's time to stop processing the log file
            log_time = get_log_time(line)
            if log_time and log_time > last_check_time:
                break

    # Write the updated player_info_data to player_info.json
    with open("player_info.json", "w") as f:
        json.dump(player_info_data, f, indent=4)

    # Write the current time to last_check_time.json
    current_time = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
    with open("last_check_time.json", "w") as f:
        json.dump({"last_check_time": current_time}, f)

# Function to read the last check time from last_check_time.json
def read_last_check_time():
    if os.path.exists("last_check_time.json") and os.path.getsize("last_check_time.json") > 0:
        with open("last_check_time.json", "r") as f:
            data = json.load(f)
            return datetime.strptime(data["last_check_time"], "%m/%d/%Y %H:%M:%S")
    return None

# Function to get the Steam nickname using the Steam API
def get_steam_nickname(steamID, api_key):
    try:
        url = f"http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={api_key}&steamids={steamID}"
        response = requests.get(url)
        data = response.json()
        return data["response"]["players"][0]["personaname"]
    except requests.RequestException as e:
        print(f"Failed to fetch Steam nickname for SteamID {steamID}: {e}")
        return "Unknown"

# Function to check if a player_steamID is already processed
def is_steamID_processed(steamID, player_info_data):
    for player_info in player_info_data:
        if player_info["player_steamID"] == steamID:
            return True
    return False

# Function to get the Steam name for a specific player_steamID
def get_steam_name_for_steamID(steamID, player_info_data):
    for player_info in player_info_data:
        if player_info["player_steamID"] == steamID:
            return player_info["player_steam_name"]
    return None

# Function to get the time from a log line
def get_log_time(line):
    try:
        time_str = line.split("[", 1)[1].split("]", 1)[0]
        return datetime.strptime(time_str, "%m/%d/%Y %H:%M:%S")
    except (ValueError, IndexError):
        return None

# Function to print player info
def print_player_info(player_info):
    print(f"Player Serial: {player_info['player_serial']}")
    print(f"Player Name: {player_info['player_name']}")
    print(f"Player SteamID: {player_info['player_steamID']}")
    print(f"Player Steam Name: {player_info['player_steam_name']}")
    print()

# Function to handle SIGTERM and SIGINT signals
def handle_signals(signum, frame):
    # Write the current time to last_check_time.json
    current_time = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
    with open("last_check_time.json", "w") as f:
        json.dump({"last_check_time": current_time}, f)

    # Exit the script
    sys.exit(0)

def main():
    # Check if the virtual environment exists and create it if it doesn't
    if not os.path.exists("venv"):
        create_virtualenv()

    # Activate the virtual environment
    activate_virtualenv()

    # Register the signal handler for SIGTERM and SIGINT
    signal.signal(signal.SIGTERM, handle_signals)
    signal.signal(signal.SIGINT, handle_signals)

    # Set the log file path
    log_file = "/home/vhserver/log/console/vhserver-console.log"

    # Set your actual Steam API key here
    api_key = "YOUR_STEAM_API_KEY"

    # Check if the script was run with the "--list" parameter
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        # Check if player_info.json exists and load its content
        if os.path.exists("player_info.json") and os.path.getsize("player_info.json") > 0:
            with open("player_info.json", "r") as f:
                player_info_data = json.load(f)
                for player_info in player_info_data:
                    print_player_info(player_info)
        else:
            print("No player information found.")
    else:
        # Check and process the log file every 10 minutes
        while True:
            if os.path.exists(log_file):
                process_log_file(log_file, api_key)
            time.sleep(600)

if __name__ == "__main__":
    main()
