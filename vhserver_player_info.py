import os
import sys
import json
import time
import subprocess
import signal
import logging
import traceback
from datetime import datetime

STEAM_API_KEY = "YOUR_STEAM_API_KEY"
LOG_FILE_PATH = "/home/vhserver/log/console/vhserver-console.log"
DAEMON_INTERVAL = 300

# Set up logging
logging.basicConfig(filename="vhserver_player_info.log", level=logging.INFO)
logger = logging.getLogger("vhserver_player_info")


class VirtualEnvironmentManager:
    @staticmethod
    def create_virtualenv():
        try:
            subprocess.check_call(["python3", "-m", "venv", "venv"])
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create virtual environment: {e}")
            sys.exit(1)

    @staticmethod
    def activate_virtualenv():
        activate_command = os.path.join("venv", "bin", "activate")
        if os.path.exists(activate_command):
            subprocess.Popen(f"source {activate_command}", shell=True, executable="/bin/bash")

    @staticmethod
    def install_required_packages():
        try:
            subprocess.check_call(["venv/bin/pip", "install", "requests"])
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install required packages: {e}")
            sys.exit(1)


class PlayerInfoProcessor:
    def __init__(self):
        self.player_data = self.load_player_data()
        self.last_check_time = self.read_last_check_time()

    def load_player_data(self):
        try:
            with open("player_database.json", "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def read_last_check_time(self):
        try:
            with open("last_check_time.json", "r") as f:
                data = json.load(f)
                return datetime.strptime(data.get("last_check_time"), "%m/%d/%Y %H:%M:%S")
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def get_steam_nickname(self, steamID):
        try:
            import requests

            url = f"http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={STEAM_API_KEY}&steamids={steamID}"
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            players = data.get("response", {}).get("players", [])
            if players:
                return players[0].get("personaname", "Unknown")
            else:
                raise ValueError("Steam API response does not contain player information.")
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch Steam nickname for SteamID {steamID}: {e}")
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            raise RuntimeError(f"Invalid response from Steam API for SteamID {steamID}: {e}")

    def is_steamID_processed(self, steamID, time_last_seen):
        return any(
            player_info["player_steamID"] == steamID and player_info.get("time_last_seen") == time_last_seen
            for player_info in self.player_data
        )

    def get_log_time(self, line):
        try:
            time_str = line.split("[", 1)[1].split("]", 1)[0]
            return datetime.strptime(time_str, "%m/%d/%Y %H:%M:%S")
        except (ValueError, IndexError):
            return None

    def update_player_data(self, player_steamID, player_steam_name, player_name, player_game_sessions, time_last_seen):
        try:
            time_last_seen = datetime.strptime(time_last_seen, "%m/%d/%Y %H:%M:%S")
        except ValueError:
            raise ValueError(f"Invalid date and time format for time_last_seen: {time_last_seen}")

        existing_player_info = next((p for p in self.player_data if p.get("player_steamID") == player_steamID), None)
        if existing_player_info:
            existing_time_last_seen = datetime.strptime(existing_player_info.get("time_last_seen", "01/01/1900 00:00:00"), "%m/%d/%Y %H:%M:%S")
            if time_last_seen > existing_time_last_seen:
                existing_player_info["player_steam_name"] = list(
                    set(existing_player_info.get("player_steam_name", []) + [player_steam_name])
                )
                existing_player_info["player_name"] = list(set(existing_player_info.get("player_name", []) + [player_name]))
                existing_player_info["player_game_sessions"] = existing_player_info.get("player_game_sessions", 0) + 1
                existing_player_info["time_last_seen"] = time_last_seen.strftime("%m/%d/%Y %H:%M:%S")
            return True
        return False

    def process_log_file(self, log_file):
        if self.last_check_time is None:
            self.last_check_time = datetime.now()

        try:
            import requests

            with open(log_file, "r") as f:
                lines = f.readlines()

                player_steamID = None
                player_steam_name = None
                player_name = None
                player_game_sessions = 0
                time_last_seen = "01/01/1900 00:00:00"

                players = {}  # Using player_steamID as the key

                for line in lines:
                    if "received local Platform ID Steam_" in line:
                        player_steamID = line.split("received local Platform ID Steam_")[1][:17]
                        time_last_seen = line[:19]

                    elif "Got character ZDOID from" in line:
                        player_name = line.split("Got character ZDOID from ")[1].split(" :")[0]
                        player_steam_name = self.get_steam_nickname(player_steamID)

                        if not self.is_steamID_processed(player_steamID, time_last_seen):
                            players[player_steamID] = {
                                "player_steam_name": [player_steam_name],
                                "player_name": [player_name],
                                "player_game_sessions": 1,
                                "time_last_seen": time_last_seen,
                            }
                        elif player_steam_name != self.get_steam_nickname(player_steamID):
                            if player_steamID not in players:
                                players[player_steamID] = {
                                    "player_steam_name": [player_steam_name],
                                    "player_name": [player_name],
                                    "player_game_sessions": 1,
                                    "time_last_seen": time_last_seen,
                                }
                            else:
                                players[player_steamID]["player_steam_name"] = list(
                                    set(players[player_steamID]["player_steam_name"] + [player_steam_name])
                                )

                    log_time = self.get_log_time(line)
                    if log_time and log_time > self.last_check_time:
                        break

            # Initialize player_data if "player_database.json" is empty
            if not self.player_data:
                self.player_data = []

            # Update player_data with aggregated data
            for player_steamID, player_info in players.items():
                self.update_player_data(player_steamID, player_info["player_steam_name"][0], player_info["player_name"][0], player_info["player_game_sessions"], player_info["time_last_seen"])

            # Add new players to player_data
            for player_steamID, player_info in players.items():
                if player_steamID not in {player.get("player_steamID") for player in self.player_data}:
                    self.player_data.append(
                        {
                            "player_steamID": player_steamID,
                            "player_steam_name": player_info["player_steam_name"],
                            "player_name": player_info["player_name"],
                            "player_game_sessions": 1,
                            "time_last_seen": player_info["time_last_seen"],
                        }
                    )

            # Write the updated player_data to player_database.json
            with open("player_database.json", "w") as f:
                json.dump(self.player_data, f, indent=4)

            current_time = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
            with open("last_check_time.json", "w") as f:
                json.dump({"last_check_time": current_time}, f)

        except Exception as e:
            logger.error(f"An error occurred while processing log file:\n{traceback.format_exc()}")


    def print_player_info(self, player_info):
        time_last_seen = player_info.get("time_last_seen", "N/A")
        try:
            formatted_time_last_seen = datetime.strptime(time_last_seen, "%m/%d/%Y %H:%M:%S").strftime("%Y/%m/%d %H:%M:%S")
        except ValueError:
            formatted_time_last_seen = "Invalid Date and Time Format"

        print(f"Player SteamID: {player_info.get('player_steamID', 'N/A')}")
        print(f"Player Steam Name: {', '.join(player_info.get('player_steam_name', ['N/A']))}")
        print(f"Player Name: {', '.join(player_info.get('player_name', ['N/A']))}")
        print(f"Game Sessions: {player_info.get('player_game_sessions', 0)}")
        print(f"Time Last Seen: {formatted_time_last_seen}")
        print()

    def print_player_database(self):
        if self.player_data:
            for player_info in self.player_data:
                self.print_player_info(player_info)
        else:
            print("No player information found.")

    def handle_signals(self, signum, frame):
        current_time = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
        with open("last_check_time.json", "w") as f:
            json.dump({"last_check_time": current_time}, f)

        sys.exit(0)


def main():
    # Check if the virtual environment exists and create it if it doesn't
    venv_manager = VirtualEnvironmentManager()
    if not os.path.exists("venv"):
        venv_manager.create_virtualenv()
        venv_manager.activate_virtualenv()
        venv_manager.install_required_packages()

    # Initialize the player info processor
    player_info_processor = PlayerInfoProcessor()

    # Register the signal handler for SIGTERM and SIGINT
    signal.signal(signal.SIGTERM, player_info_processor.handle_signals)
    signal.signal(signal.SIGINT, player_info_processor.handle_signals)

    # Check if the script was run with the "--daemon" parameter
    if len(sys.argv) > 1 and sys.argv[1] == "--daemon":
        try:
            while True:
                if os.path.exists(LOG_FILE_PATH):
                    player_info_processor.process_log_file(LOG_FILE_PATH)
                time.sleep(DAEMON_INTERVAL)
        except Exception as e:
            logger.error(f"An unexpected error occurred in the daemon:\n{traceback.format_exc()}")
            sys.exit(1)
    else:
        player_info_processor.print_player_database()


if __name__ == "__main__":
    main()
