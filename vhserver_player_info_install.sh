#!/bin/bash

# Function to log messages to a log file
log() {
    echo $1
    echo ""
    echo "$(date +'%Y-%m-%d %H:%M:%S') - $1" >> vhserver_player_info_install.log
}

# Check if the script is run as root
if [[ $(id -u) -ne 0 ]]; then
    log "This script requires root permissions. Please run it with 'sudo'."
    exit 1
fi

# Check if the user 'vhserver' exists
if ! id "vhserver" &>/dev/null; then
    log "User 'vhserver' does not exist. Please install the lgsm server and follow their instructions to create the 'vhserver' user."
    exit 1
fi

# Check if the required folders and file exist
if [[ ! -d "/home/vhserver/lgsm/" || ! -f "/home/vhserver/log/console/vhserver-console.log" ]]; then
    log "Please install the Valheim lgsm server first before running this script and run it once."
    exit 1
fi

# Check if the required files exist
if [[ ! -f "vhserver_player_info.py" || ! -f "vhserver_player_info_logrotate.conf" || ! -f "vhserver_player_info.service" ]]; then
    log "Required files are missing. Please download them from https://github.com/adevnylo/lgsm-vhserver-player-info"
    exit 1
fi

# Create the '/home/vhserver/player_info' folder with owner 'vhserver:vhserver'
mkdir -p /home/vhserver/player_info
chown vhserver:vhserver /home/vhserver/player_info
log 'Folder "player_info" created in /home/vhserver/'

# Move 'vhserver_player_info.py' to the new folder and make it executable
cp vhserver_player_info.py /home/vhserver/player_info/
chmod +x /home/vhserver/player_info/vhserver_player_info.py
log 'File "vhserver_player_info.py" copied to the player_info folder and made it executable'

# Create empty files inside the 'player_info' folder
touch /home/vhserver/player_info/player_database.json
touch /home/vhserver/player_info/last_check_time.json
touch /home/vhserver/player_info/vhserver_player_info.log
touch /home/vhserver/player_info/vhserver_player_info_service_error.log
touch /home/vhserver/player_info/vhserver_player_info_service_output.log
chmod 0644 /home/vhserver/player_info/vhserver_player_info_service_output.log
log 'Created 5 empty files ("player_database.json", "last_check_time.json", "vhserver_player_info.log", "vhserver_player_info_service_error.log", and "vhserver_player_info_service_output.log") inside the player_info folder, which will be used by vhserver_player_info.py'

# Set ownership for all files inside the 'player_info' folder to 'vhserver:vhserver'
chown vhserver:vhserver /home/vhserver/player_info/*
log "Set ownership of all files inside the player_info folder to vhserver:vhserver"

# Move 'vhserver_player_info_logrotate.conf' to '/etc/logrotate.d/'
cp vhserver_player_info_logrotate.conf /etc/logrotate.d/
log 'File "vhserver_player_logrotate.conf" copied to /etc/logrotate.d/'

# Move 'vhserver_player_info.service' to '/etc/systemd/system/'
cp vhserver_player_info.service /etc/systemd/system/
log 'File "vhserver_player_info.service" copied to /etc/systemd/system/'

# Reload systemd daemon
log "Reloading the systemd daemon..."
systemctl daemon-reload

# Restart logrotate
log "Restarting the logrotate service..."
systemctl restart logrotate

# Enable and start the new systemd service
log "Enabling and starting the vhserver_player_info service..."
systemctl enable vhserver_player_info.service
systemctl start vhserver_player_info.service

log "Installation completed successfully!"
echo "You can print your Valheim server's player database by running:"
echo ""
echo "python3 /home/vhserver/player_info/vhserver_player_info.py"
echo ""
