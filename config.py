# This file is part of Mantib.

# Mantib is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Mantib is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Mantib.  If not, see <http://www.gnu.org/licenses/>.

"""Config Module

Config -- Basic configuration/settings for Mantib

"""

import os
import sqlite3

USERS = """CREATE TABLE IF NOT EXISTS users (
ID INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
name VARCHAR(32),
password VARCHAR(32),
iv VARCHAR(16),
grouplist VARCHAR(256),
ssh_access INTEGER DEFAULT(1),
rcon_access INTEGER DEFAULT(1)
)"""
GROUPS = """CREATE TABLE IF NOT EXISTS groups (
ID INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
name VARCHAR(32),
description TEXT
)"""
SERVERS = """CREATE TABLE IF NOT EXISTS servers (
ID INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
name VARCHAR(32),
ipaddress VARCHAR(45),
GID INTEGER REFERENCES groups (ID),
ssh_username VARCHAR(32),
ssh_password VARCHAR(64),
ssh_port VARCHAR(10),
rcon_password VARCHAR(64),
rcon_port VARCHAR(10)
)"""
CONFIG = """CREATE TABLE IF NOT EXISTS config (
UID INTEGER UNIQUE DEFAULT(1),
enable_status_ssh INTEGER DEFAULT(1),
enable_status_rcon INTEGER DEFAULT(1),
status_ssh_maxtime INTEGER DEFAULT(10),
status_rcon_maxtime INTEGER DEFAULT(10),
max_rcon_attempts INTEGER DEFAULT(5),
enable_debuglog INTEGER DEFAULT(0),
daemon_check VARCHAR(256) DEFAULT('ps auxww|grep {IP}|grep SCREEN|grep -v grep'),
dcheck_return VARCHAR(256) DEFAULT('{ANY}'),
daemon_start VARCHAR(256) DEFAULT('screen -wipe;cd ~/srcds_l;./start.sh;{P:3};{DCHECK}'),
dstart_return VARCHAR(256) DEFAULT('{ANY}'),
daemon_stop VARCHAR(256) DEFAULT('screen -wipe;cd ~/srcds_l;./stop.sh;{P:3};{DCHECK}'),
dstop_return VARCHAR(256) DEFAULT('{ANY}'),
daemon_update_check VARCHAR(256) DEFAULT('cd ~/srcds_l;tail nohup.out -n 10;./steam -command version | grep -v CAsyncIOManager'),
ducheck_return VARCHAR(256) DEFAULT('{ANY}'),
daemon_update_start VARCHAR(256) DEFAULT('cd ~/srcds_l/;./update_updater.exp;cd ~/srcds_l;rm -rf nohup.out;./update.sh'),
dustart_return VARCHAR(256) DEFAULT('{ANY}'),
daemon_update_stop VARCHAR(256) DEFAULT('cd ~/srcds_l;rm -rf nohup.out;./update_stop.sh;'),
dustop_return VARCHAR(256) DEFAULT('{ANY}')
)"""

class Config:
    """Basic configuration/settings for Mantib

    Public functions:
    __init__ -- Make sure database exists
    connect -- Connects to the database
    save -- Saves the database without closing it
    close -- Closes connection to the database

    """

    def __init__(self):
        exist = os.path.isfile("Mantib.db")
        if exist == False:
            self.conn = sqlite3.connect('Mantib.db')
            self.c = self.conn.cursor()
            self.c.execute(USERS)
            self.c.execute(GROUPS)
            self.c.execute(SERVERS)
            self.c.execute(CONFIG)
            self.conn.commit()
            self.c.close()
            self.conn.close()

    def connect(self):
        self.conn = sqlite3.connect('Mantib.db')
        self.c = self.conn.cursor()

    def save(self):
        self.conn.commit()

    def close(self, save=0):
        if int(save) == 1: self.conn.commit()
        self.c.close()
        self.conn.close()