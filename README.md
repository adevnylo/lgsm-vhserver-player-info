# lgsm-vhserver-player-info
Python script, systemd service, and logrotate conf to enable player info collection on a self-hosted Valheim server using the LinuxGSM installer/manager.

As of now, the script assumes that you have all the requirements already installed on your system to create a Python virtual environment and that you have PIP to install the "requests" module in the virtual environment.
Future revisions will automatically install all required packages based on your Linux distro.

**To Do:**
- Add a parameter to check for a specific player's info with the user-provided Steam ID as a search parameter.
- Modify the install shell script to make it so a user could run it directly from GitHub, download the required files, and install all dependencies based on the Linux distro at runtime.
- Add a functionality to the install shell script where the user can input their Steam API key, which will be written in the main Python script (or an external config file).

**Wishlist:**
- Add a "connections.log" file where all player connections and disconnections are logged in a easily readable format.
- Make a Discord bot that would handle all player info requests through bot commands on Discord itself, and display the result (be it a specific player's info or the whole database) with an embed message.
  - The user can enable or disable this functionality in the configuration file (default "off").
  - The bot could also remind players about scheduled server restarts by pinging them on Discord.
    - This would require manually editing the player_database.json and adding a player_discordID value for each player.
    - Alternatively, it could be done using a bot command that would receive as inputs the player steamID and discordID (or extrapolate it from a user mention), and it would then automatically edit the database entry for that player.

*This is my first project on GitHub, so please bear with me.*
