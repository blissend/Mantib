#!/usr/bin/env python
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

import os
import sys
import random # For random IV in pycrypto encrypting/decrpyting
import hashlib # For MD5 account pass encryption (seperate from pycrypto)
import socket # For testing if valid IP
import string # For generating characters in random IV
import paramiko # For SSH functionality
import SRCDS # For RCON functionality
import wx
import wx.richtext as rt
import wx.xrc as xrc
import wx.lib.agw.flatnotebook as fnb
import wx.lib.agw.ultimatelistctrl as ulc
from wx.lib.wordwrap import wordwrap # For wrapping words in about dialog
from Crypto.Cipher import AES # Encrypt/Decrypt passwords in sqlite
import binascii # For unhexlify function, needed by pycrypto decryption
import config # For easy sqlite connections and creation
import thread # For threading server online activity checks
import re # Used for filtering out VT100 escape codes
from time import sleep # For the daemon commands and pausing for a bit
import csv # For import/export server group operations
import logging
import logging.handlers # Used to fine tune log rotation

LICENSE = """Mantib - A portable game server management app.
Copyright (C) 2012  Adam Carlin

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>."""
NOTES = """DAEMON COMMANDS

This area can control the commands sent by actions you initiate such as starting
and stopping a daemon. If you aren't familiar with Linux commands it's
probably better to leave this area alone.

For those who are familiar, there a few special tags you should know and
how return results work. First the tags...

{DCHECK} - Inserts the saved Daemon Check command
{DSTART} - Inserts the saved Daemon Start command
{DSTOP} - Inserts the saved Daemon Stop command
{DUCHECK} - Inserts the saved Daemon Update Check command
{DUSTART} - Inserts the saved Daemon Update Start command
{DUSTOP} - Inserts the saved Daemon Update Stop command
{IP} - Inserts the saved IP for the server you're performing an action on
{ANY} - Look for any response
{NONE} - Expect no response
{NULL} - Command/Response does not matter
{SESSION} - Runs the command in the stripped down interactive SSH terminal

Note that you must enclose the tag with curly brackets and use upper case.

As you may have seen, some tags are designed only for the return field. Using
them will help inform you the command succeeded. For the Daemon Check field
it'll help prevent running a command if the daemon is already running or not. If
you don't care for that, then simply use the NULL tag to cancel those checks.
Also, you can specify an exact return value of the last line rather than using
tags.

Finally, the SESSION tag will send the command to an interactive SSH shell
built into Mantib. This is usesful for something you want to trail a long
output with. It doesn't not matter where you place this tag, if it's seen, it'll
send the entire command to the SSH terminal.
"""
RESOURCE = os.environ.get('_MEIPASS2',os.path.abspath('.'))
XML = os.path.join(RESOURCE, 'xml')
IMG = os.path.join(RESOURCE, 'images')

class Mantib(wx.App):
    def OnInit(self):
        self.sql = config.Config()
        path = os.path.join(XML,'Mantib.xrc')
        self.res = xrc.XmlResource(path)
        self.init_frame()
        return True

    def init_frame(self):
        # Initiate controls with blank display
        self.frame = self.res.LoadFrame(None, 'm_frame')
        logo = os.path.join(IMG, 'mantiblogo.ico')
        ico = wx.Icon(logo, wx.BITMAP_TYPE_ICO)
        self.frame.SetIcon(ico)

        # Menubar controls
        self.menubar = self.res.LoadMenuBarOnFrame(self.frame, 'm_menubar')
        self.mb_enable_ssh = self.menubar.FindItemById(
            xrc.XRCID('enable_status_ssh'))
        self.mb_enable_rcon = self.menubar.FindItemById(
            xrc.XRCID('enable_status_rcon'))
        self.mb_group_import = self.menubar.FindItemById(
            xrc.XRCID('group_import'))
        self.mb_group_export = self.menubar.FindItemById(
            xrc.XRCID('group_export'))

        # Toolbar controls, disabled on startup
        #self.toolbar = self.frame.FindWindowByName('m_toolbar')
        self.toolbar = self.frame.CreateToolBar(
            wx.TB_HORIZONTAL|wx.NO_BORDER|wx.TB_FLAT)
        group_add = wx.Bitmap(
            os.path.join(IMG, 'group_add.png'), wx.BITMAP_TYPE_PNG)
        group_edit = wx.Bitmap(
            os.path.join(IMG, 'group_edit.png'), wx.BITMAP_TYPE_PNG)
        group_delete = wx.Bitmap(
            os.path.join(IMG, 'group_delete.png'), wx.BITMAP_TYPE_PNG)
        group_go = wx.Bitmap(
            os.path.join(IMG, 'group_go.png'), wx.BITMAP_TYPE_PNG)
        server_add = wx.Bitmap(
            os.path.join(IMG, 'server_add.png'), wx.BITMAP_TYPE_PNG)
        server_edit = wx.Bitmap(
            os.path.join(IMG, 'server_edit.png'), wx.BITMAP_TYPE_PNG)
        server_key = wx.Bitmap(
            os.path.join(IMG, 'server_key.png'), wx.BITMAP_TYPE_PNG)
        server_delete = wx.Bitmap(
            os.path.join(IMG, 'server_delete.png'), wx.BITMAP_TYPE_PNG)
        arrow_right = wx.Bitmap(
            os.path.join(IMG, 'arrow_right.png'), wx.BITMAP_TYPE_PNG)
        stop = wx.Bitmap(
            os.path.join(IMG, 'stop.png'), wx.BITMAP_TYPE_PNG)
        transmit_add = wx.Bitmap(
            os.path.join(IMG, 'transmit_add.png'), wx.BITMAP_TYPE_PNG)
        transmit_delete = wx.Bitmap(
            os.path.join(IMG, 'transmit_delete.png'), wx.BITMAP_TYPE_PNG)
        transmit_go = wx.Bitmap(
            os.path.join(IMG, 'transmit_go.png'), wx.BITMAP_TYPE_PNG)
        xp_term = wx.Bitmap(
            os.path.join(IMG, 'application_xp_terminal.png'),
            wx.BITMAP_TYPE_PNG)
        osx_term = wx.Bitmap(
            os.path.join(IMG, 'application_osx_terminal.png'),
            wx.BITMAP_TYPE_PNG)
        self.toolbar.AddLabelTool(
            10, 'Group Add', group_add, shortHelp='Group Add',
            longHelp='Add a new group.')
        self.toolbar.AddLabelTool(
            20, 'Group Edit', group_edit, shortHelp='Group Edit',
            longHelp='Edit selected group name.')
        self.toolbar.AddLabelTool(
            30, 'Group Delete', group_delete, shortHelp='Group Delete',
            longHelp='This will open a group selection window.')
        self.toolbar.AddLabelTool(
            40, 'Reload Groups', group_go, shortHelp='Reload Groups',
            longHelp='Reloads the groups associated with this user.')
        self.toolbar.AddSeparator()
        self.toolbar.AddLabelTool(
            50, 'Server Add', server_add, shortHelp='Server Add',
            longHelp='Add a new server.')
        self.toolbar.AddLabelTool(
            60, 'Server Edit', server_edit, shortHelp='Server Edit',
            longHelp='Edit selected server.')
        self.toolbar.AddLabelTool(
            70, 'Server Key', server_key, shortHelp='Server Key',
            longHelp='Reveal selected server passwords.')
        self.toolbar.AddLabelTool(
            80, 'Server Delete', server_delete, shortHelp='Server Delete',
            longHelp='Delete selected server.')
        self.toolbar.AddSeparator()
        self.toolbar.AddLabelTool(
            90, 'Daemon Start', arrow_right, shortHelp='Daemon Start',
            longHelp='Start the daemon for the selected server.')
        self.toolbar.AddLabelTool(
            100, 'Daemon Stop', stop, shortHelp='Daemon Stop',
            longHelp='Stop the daemon for the selected server.')
        self.toolbar.AddLabelTool(
            110, 'Daemon Update Start', transmit_add,
            shortHelp='Daemon Update Start',
            longHelp='Start the daemon update for the selected server.')
        self.toolbar.AddLabelTool(
            120, 'Daemon Update Stop', transmit_delete,
            shortHelp='Daemon Update Stop',
            longHelp='Stop the daemon update for the selected server.')
        self.toolbar.AddLabelTool(
            130, 'Daemon Update Check', transmit_go,
            shortHelp='Daemon Update Check',
            longHelp='Check the daemon update for the selected server.')
        self.toolbar.AddSeparator()
        self.toolbar.AddLabelTool(
            140, 'SSH Terminal', xp_term, shortHelp='SSH Terminal',
            longHelp='Opens a stripped down SSH shell window for ' +
            'the selected server.')
        self.toolbar.AddLabelTool(
            150, 'RCON Terminal', osx_term, shortHelp='RCON Terminal',
            longHelp='Opens a basic RCON window to selected server')
        self.toolbar.Realize()
        self.enable_tooblar(False)

        # Top half
        self.servers_panel = xrc.XRCCTRL(self.frame, 'm_servers_panel')
        self.server_nb = fnb.FlatNotebook(
            self.servers_panel,
            agwStyle=fnb.FNB_RIBBON_TABS|fnb.FNB_NAV_BUTTONS_WHEN_NEEDED|
            fnb.FNB_BACKGROUND_GRADIENT|fnb.FNB_NO_X_BUTTON)
        self.res.AttachUnknownControl(
            'm_auin_servers', self.server_nb, self.servers_panel)

        # Bottom half
        self.logger_panel = xrc.XRCCTRL(self.frame, 'm_logger_panel')
        self.logger_nb = fnb.FlatNotebook(
            self.logger_panel,
            agwStyle=fnb.FNB_BOTTOM|fnb.FNB_NO_X_BUTTON|
            fnb.FNB_NAV_BUTTONS_WHEN_NEEDED)
        self.res.AttachUnknownControl(
            'm_auin_logger', self.logger_nb, self.logger_panel)
        self.logger = rt.RichTextCtrl(
            self.logger_nb, -1, style=wx.VSCROLL|wx.TE_READONLY)
        # Create logger image list
        path = os.path.join(IMG, 'table.png')
        table = wx.Bitmap(path, wx.BITMAP_TYPE_PNG)
        path = os.path.join(IMG, 'table_edit.png')
        table_edit = wx.Bitmap(path, wx.BITMAP_TYPE_PNG)
        image_list = ulc.PyImageList(16, 16)
        image_list.Add(table)
        image_list.Add(table_edit)
        self.logger_nb.SetImageList(image_list)
        # Logger Page
        self.logger_nb.AddPage(self.logger, "Logger", imageId=0)
        self.logger.GetCaret().Hide()
        self.text_attr = rt.RichTextAttr()
        # SSH Page
        self.ssh_panel = self.res.LoadPanel(self.logger_nb, 'ssh_panel')
        self.ssh_logger = rt.RichTextCtrl(
            self.ssh_panel, -1, style=wx.VSCROLL|wx.TE_READONLY)
        self.res.AttachUnknownControl(
            'ssh_logger', self.ssh_logger, self.ssh_panel)
        self.ssh_cmd = xrc.XRCCTRL(self.ssh_panel, 'ssh_cmd')
        self.logger_nb.AddPage(self.ssh_panel, "SSH")
        # RCON Page
        self.rcon_panel = self.res.LoadPanel(self.logger_nb, 'rcon_panel')
        self.rcon_logger = rt.RichTextCtrl(
            self.rcon_panel, -1, style=wx.VSCROLL|wx.TE_READONLY)
        self.res.AttachUnknownControl(
            'rcon_logger', self.rcon_logger, self.rcon_panel)
        self.rcon_cmd = xrc.XRCCTRL(self.rcon_panel, 'rcon_cmd')
        self.logger_nb.AddPage(self.rcon_panel, "RCON")

        # Toolbar events
        self.frame.Bind(wx.EVT_TOOL, self.group_add, id=10)
        self.frame.Bind(wx.EVT_TOOL, self.group_edit, id=20)
        self.frame.Bind(wx.EVT_TOOL, self.group_delete, id=30)
        self.frame.Bind(wx.EVT_TOOL, self.reload_groups, id=40)
        self.frame.Bind(wx.EVT_TOOL, self.server_add, id=50)
        self.frame.Bind(wx.EVT_TOOL, self.server_edit, id=60)
        self.frame.Bind(wx.EVT_TOOL, self.server_key, id=70)
        self.frame.Bind(wx.EVT_TOOL, self.server_delete, id=80)
        self.frame.Bind(
            wx.EVT_TOOL,
            lambda event: self.daemon_action(event, 'Daemon Start'), id=90)
        self.frame.Bind(
            wx.EVT_TOOL,
            lambda event: self.daemon_action(event, 'Daemon Stop'), id=100)
        self.frame.Bind(
            wx.EVT_TOOL,
            lambda event: self.daemon_action(event, 'Daemon Update Start'),
            id=110)
        self.frame.Bind(
            wx.EVT_TOOL,
            lambda event: self.daemon_action(event, 'Daemon Update Stop'),
            id=120)
        self.frame.Bind(
            wx.EVT_TOOL,
            lambda event: self.daemon_action(event, 'Daemon Update Check'),
            id=130)
        self.frame.Bind(wx.EVT_TOOL, self.ssh_connect, id=140)
        self.frame.Bind(wx.EVT_TOOL, self.rcon_connect, id=150)
        # Menu events
        self.frame.Bind(wx.EVT_MENU, self.new_user, id=xrc.XRCID('new_user'))
        self.frame.Bind(wx.EVT_MENU, self.sign_in, id=xrc.XRCID('sign_in'))
        self.frame.Bind(
            wx.EVT_MENU, self.group_import, id=xrc.XRCID('group_import'))
        self.frame.Bind(
            wx.EVT_MENU, self.group_export, id=xrc.XRCID('group_export'))
        self.frame.Bind(wx.EVT_MENU, self.about, id=xrc.XRCID('about_mantib'))
        self.frame.Bind(
            wx.EVT_MENU, self.toggle_menu,
            id=xrc.XRCID('enable_status_ssh'))
        self.frame.Bind(
            wx.EVT_MENU, self.toggle_menu,
            id=xrc.XRCID('enable_status_rcon'))
        self.frame.Bind(wx.EVT_MENU, self.settings, id=xrc.XRCID('preferences'))
        self.frame.Bind(wx.EVT_MENU, self.exit, id=xrc.XRCID('exit'))
        # Misc events
        self.frame.Bind(
            wx.EVT_TEXT_ENTER, self.ssh_command, id=xrc.XRCID('ssh_cmd'))
        self.frame.Bind(
            wx.EVT_TEXT_ENTER, self.rcon_command, id=xrc.XRCID('rcon_cmd'))
        self.frame.Bind(ulc.EVT_LIST_ITEM_ACTIVATED, self.server_edit)
        # Proper function name is essential for utilizing event
        self.logger_nb.Bind(
            fnb.EVT_FLATNOTEBOOK_PAGE_CHANGED, self.OnPageChanged)

        # Set initial sizes and show it
        self.frame.SetSize((720,550))
        self.frame.SetMinSize((720,550))
        self.frame.Center()
        self.frame.Show()

        # Check database and initialize data
        self.init_data()

    def init_data(self):
        # Public variables
        self.user = {
            'UID': -1, 'username': -1, 'password': -1, 'IV': -1, 'key': -1}
        self.settings = {}
        self.groups = {}
        self.group_order = ''
        self.server_ulc = {}
        self.client = {'ssh': -1, 'chan': -1, 'rcon': -1}
        self.server_status = {}
        # Custom dialogs needing state flags on opened/closed stats
        self.dialogs = {
            'new_user': 0, 'sign_in': 0, 'new_group': 0,
            'new_server': 0, 'server_edit': 0, 'settings': 0}
        # To help remember former server name when editing
        self.server_edit_name = ''
        self.timer = wx.Timer(self)
        self.timer.Start(1000)
        self.timer_stats = {'init': 0, 'ssh_count': 0, 'rcon_count': 0}
        self.Bind(wx.EVT_TIMER, self.on_timer)

        # Determine if database exists, if not create
        self.sql.connect()
        results = self.sql.c.execute("SELECT count(*) FROM users LIMIT 1")
        for row in results:
            if row[0] == 0:
                action = 0
            else:
                action = 1
        self.sql.close()
        if action == 0:
            self.new_user(wx.EVT_MENU)
        else:
            self.sign_in(wx.EVT_MENU)

    def on_timer(self, event):
        # Make sure we're logged in before doing timer stuff
        if self.user['UID'] == -1 or len(self.server_status) == 0:
            return

        if self.timer_stats['init'] == 0:
            self.timer_stats['ssh_count'] = (
                self.settings['status_ssh_maxtime'])
            self.timer_stats['rcon_count'] = (
                self.settings['status_rcon_maxtime'])
            self.timer_stats['init'] = 1
        else:
            if self.settings['enable_status_ssh'] == 1:
                self.timer_stats['ssh_count'] += 1
            if self.settings['enable_status_rcon'] == 1:
                self.timer_stats['rcon_count'] += 1
        if (self.timer_stats['ssh_count'] >=
            self.settings['status_ssh_maxtime'] and
            self.settings['enable_status_ssh'] == 1):
            for server_name in self.server_status:
                GID = self.server_status[server_name]['GID']
                try:
                    index = self.server_ulc[GID].FindItem(-1, server_name)
                except:
                    print 'FAILURE'
                self.server_status[server_name]['index'] = index
                thread.start_new_thread(self.ssh_check, (server_name,))
            self.timer_stats['ssh_count'] = 0
        if (self.timer_stats['rcon_count'] >=
            self.settings['status_rcon_maxtime'] and
            self.settings['enable_status_rcon'] == 1):
            for server_name in self.server_status:
                GID = self.server_status[server_name]['GID']
                index = self.server_ulc[GID].FindItem(-1, server_name)
                self.server_status[server_name]['index'] = index
                thread.start_new_thread(self.rcon_check, (server_name,))
            self.timer_stats['rcon_count'] = 0

    def ssh_check(self, data):
        # One threaded function for ssh checks
        name = data
        ipaddress = self.server_status[name]['ipaddress']
        ssh_port = self.server_status[name]['ssh_port']
        rcon_port = self.server_status[name]['rcon_port']
        ssh_status = self.server_status[name]['ssh_status']
        index = self.server_status[name]['index']
        GID = self.server_status[name]['GID']
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((ipaddress, int(ssh_port)))
        except Exception, e:
            # Must account for server being deleted during check time
            if ssh_status != 'Bad' and name in self.server_status:
                self.server_status[name]['ssh_status'] = 'Bad'
                new_data = [GID, name, index]
                wx.CallAfter(self.add_ulc_data, new_data)
        else:
            # Must account for server being deleted during check time
            if ssh_status != 'Good' and name in self.server_status:
                self.server_status[name]['ssh_status'] = 'Good'
                new_data = [GID, name, index]
                wx.CallAfter(self.add_ulc_data, new_data)
        s.close()

    def rcon_check(self, data):
        # One threaded function for rcon checks
        name = data
        GID = self.server_status[name]['GID']
        ipaddress = self.server_status[name]['ipaddress']
        rcon_port = self.server_status[name]['rcon_port']
        player_status = self.server_status[name]['player_status']
        rcon_pass = self.server_status[name]['rcon_password']
        rcon_attempts = self.server_status[name]['rcon_attempts']
        index = self.server_status[name]['index']
        if (player_status != 'Bad' and
            rcon_attempts < self.settings['max_rcon_attempts']):
            try:
                r = SRCDS.SRCDS(ipaddress, rconpass=rcon_pass, timeout=3)
                info, players = r.status()
            except:
                if name in self.server_status:
                    self.server_status[name]['rcon_attempts'] += 1
                    rcon_attempts += 1
                    if rcon_attempts < self.settings['max_rcon_attempts']:
                        self.server_status[name]['rcon_status'] = 'N/A'
                    else:
                        self.server_status[name]['rcon_status'] = 'Bad'
                        self.server_status[name]['player_status'] = 'N/A'
                        self.server_status[name]['map'] = 'N/A'
                        self.server_status[name]['version'] = 'N/A'
                    text = (
                        str(self.server_status[name]['rcon_attempts']) +
                        ' failed RCON attempt for "' + name + '".')
                    wx.CallAfter(self.output, text, 'RCON Check')
                    new_data = [GID, name, index]
                    wx.CallAfter(self.add_ulc_data, new_data)
            else:
                r.disconnect()
                if name in self.server_status:
                    self.server_status[name]['rcon_status'] = 'Good'
                    status = (str(info['current_playercount']) + '/' +
                              str(info['max_players']))
                    self.server_status[name]['player_status'] = status
                    self.server_status[name]['map'] = info['current_map']
                    self.server_status[name]['version'] = info['version']
                    self.server_status[name]['rcon_attempts'] = 0
                    new_data = [GID, name, index]
                    wx.CallAfter(self.add_ulc_data, new_data)

    def exit(self, event):
        self.timer.Stop()
        self.ssh_disconnect()
        self.frame.Close()
        self.Exit()

    def about(self, event):
        info = wx.AboutDialogInfo()
        info.Name = "Mantib"
        info.Version = "2012.06.08.1"
        info.Copyright = "(C) 2012 Adam Carlin"
        info.Description = wordwrap(
            "A portable cross-platform application to manage Valve "
            "daemons running on Linux/Cygwin servers.",
            300, wx.ClientDC(self.frame))
        info.WebSite = ("http://www.blissend.com/mantib", "Mantib Website")
        info.Developers = ["Adam Carlin", "Adam's \"Imaginary Friend\""]
        license_text = LICENSE
        info.Licence = wordwrap(license_text,
            500, wx.ClientDC(self.frame), breakLongWords=False)
        wx.AboutBox(info)

    def settings(self, event):
        # NOTE: Linux can't use XRC textctrl as multiline, use unknown control

        # Make sure user is loaded
        if self.user['UID'] == -1:
            return

        # Make sure we only open one of these dialogs
        for dlg in self.dialogs:
            if self.dialogs[dlg] == 1:
                return
        if self.dialogs['settings'] == 0:
            self.dialogs['settings'] = 1
        elif self.dialogs['settings'] == 1:
            return

        self.msd_dlg = self.res.LoadDialog(self.frame, 'msd_dlg')
        self.msd_dlg.SetWindowStyle(
            wx.DEFAULT_DIALOG_STYLE|wx.TAB_TRAVERSAL|wx.RESIZE_BORDER)
        self.msd_nb = xrc.XRCCTRL(self.msd_dlg, 'msd_nb')
        # General page
        self.msd_enable_sshstatus = xrc.XRCCTRL(
            self.msd_dlg, 'msd_enable_sshstatus')
        if self.settings['enable_status_ssh'] == 1:
            self.msd_enable_sshstatus.SetValue(True)
        else:
            self.msd_enable_sshstatus.SetValue(False)
        self.msd_enable_rconstatus = xrc.XRCCTRL(
            self.msd_dlg, 'msd_enable_rconstatus')
        if self.settings['enable_status_rcon'] == 1:
            self.msd_enable_rconstatus.SetValue(True)
        else:
            self.msd_enable_rconstatus.SetValue(False)
        self.msd_sshstatus_time = xrc.XRCCTRL(
            self.msd_dlg, 'msd_sshstatus_time')
        self.msd_sshstatus_time.SetValue(
            str(self.settings['status_ssh_maxtime']))
        self.msd_rconstatus_time = xrc.XRCCTRL(
            self.msd_dlg, 'msd_rconstatus_time')
        self.msd_rconstatus_time.SetValue(
            str(self.settings['status_rcon_maxtime']))
        self.msd_max_rcon_attempts = xrc.XRCCTRL(
            self.msd_dlg, 'msd_max_rcon_attempts')
        self.msd_max_rcon_attempts.SetValue(
            str(self.settings['max_rcon_attempts']))
        self.msd_enable_sshstatus = xrc.XRCCTRL(
            self.msd_dlg, 'msd_enable_sshstatus')
        self.msd_enable_debuglog = xrc.XRCCTRL(
            self.msd_dlg, 'msd_enable_debuglog')
        if self.settings['enable_debuglog'] == 1:
            self.msd_enable_debuglog.SetValue(True)
        else:
            self.msd_enable_debuglog.SetValue(False)
        # Actions page
        self.msd_scrolled = self.msd_dlg.FindWindowByName('daemon_panel')
        # Actions page - DCheck
        self.msd_daemon_check = wx.TextCtrl(
            self.msd_scrolled, -1, style=wx.TE_MULTILINE|wx.TE_WORDWRAP)
        self.msd_daemon_check.SetMinSize((100,50))
        self.res.AttachUnknownControl(
            'daemon_check_cmd', self.msd_daemon_check, self.msd_scrolled)
        self.msd_daemon_check.SetValue(
            str(self.settings['daemon_check']))
        self.msd_dcheck_return = xrc.XRCCTRL(
            self.msd_scrolled, 'dcheck_return')
        self.msd_dcheck_return.SetValue(
            str(self.settings['dcheck_return']))
        # Daemon page - DStart
        self.msd_daemon_start = wx.TextCtrl(
            self.msd_scrolled, -1, style=wx.TE_MULTILINE|wx.TE_WORDWRAP)
        self.msd_daemon_start.SetMinSize((100,50))
        self.res.AttachUnknownControl(
            'daemon_start_cmd', self.msd_daemon_start, self.msd_scrolled)
        self.msd_daemon_start.SetValue(
            str(self.settings['daemon_start']))
        self.msd_dstart_return = xrc.XRCCTRL(
            self.msd_scrolled, 'dstart_return')
        self.msd_dstart_return.SetValue(
            str(self.settings['dstart_return']))
        # Daemon page - DStop
        self.msd_daemon_stop = wx.TextCtrl(
            self.msd_scrolled, -1, style=wx.TE_MULTILINE|wx.TE_WORDWRAP)
        self.msd_daemon_stop.SetMinSize((100,50))
        self.res.AttachUnknownControl(
            'daemon_stop_cmd', self.msd_daemon_stop, self.msd_scrolled)
        self.msd_daemon_stop.SetValue(
            str(self.settings['daemon_stop']))
        self.msd_dstop_return = xrc.XRCCTRL(
            self.msd_scrolled, 'dstop_return')
        self.msd_dstop_return.SetValue(
            str(self.settings['dstop_return']))
        # Daemon page - DUCheck
        self.msd_daemon_update_check = wx.TextCtrl(
            self.msd_scrolled, -1, style=wx.TE_MULTILINE|wx.TE_WORDWRAP)
        self.msd_daemon_update_check.SetMinSize((100,50))
        self.res.AttachUnknownControl(
            'daemon_update_check_cmd',
            self.msd_daemon_update_check, self.msd_scrolled)
        self.msd_daemon_update_check.SetValue(
            str(self.settings['daemon_update_check']))
        self.msd_ducheck_return = xrc.XRCCTRL(
            self.msd_scrolled, 'ducheck_return')
        self.msd_ducheck_return.SetValue(
            str(self.settings['ducheck_return']))
        # Daemon page - DUStart
        self.msd_daemon_update_start = wx.TextCtrl(
            self.msd_scrolled, -1, style=wx.TE_MULTILINE|wx.TE_WORDWRAP)
        self.msd_daemon_update_start.SetMinSize((100,50))
        self.res.AttachUnknownControl(
            'daemon_update_start_cmd',
            self.msd_daemon_update_start, self.msd_scrolled)
        self.msd_daemon_update_start.SetValue(
            str(self.settings['daemon_update_start']))
        self.msd_dustart_return = xrc.XRCCTRL(
            self.msd_scrolled, 'dustart_return')
        self.msd_dustart_return.SetValue(
            str(self.settings['dustart_return']))
        # Daemon page - DUStop
        self.msd_daemon_update_stop = wx.TextCtrl(
            self.msd_scrolled, -1, style=wx.TE_MULTILINE|wx.TE_WORDWRAP)
        self.msd_daemon_update_stop.SetMinSize((100,50))
        self.res.AttachUnknownControl(
            'daemon_update_stop_cmd',
            self.msd_daemon_update_stop, self.msd_scrolled)
        self.msd_daemon_update_stop.SetValue(
            str(self.settings['daemon_update_stop']))
        self.msd_dustop_return = xrc.XRCCTRL(
            self.msd_scrolled, 'dustop_return')
        self.msd_dustop_return.SetValue(
            str(self.settings['dustop_return']))
        # General txt labels
        self.msd_statusssh_txt = xrc.XRCCTRL(
            self.msd_dlg, 'msd_statusssh_txt')
        self.msd_statusrcon_txt = xrc.XRCCTRL(
            self.msd_dlg, 'msd_statusrcon_txt')
        self.max_rcon_attempts_txt = xrc.XRCCTRL(
            self.msd_dlg, 'msd_max_rcon_attempts_txt')
        # Daemon txt labels
        self.msd_daemon_check_txt = xrc.XRCCTRL(
            self.msd_scrolled, 'daemon_check_txt')
        self.msd_dcheck_return_txt = xrc.XRCCTRL(
            self.msd_scrolled, 'dcheck_return_txt')
        self.msd_daemon_start_txt = xrc.XRCCTRL(
            self.msd_scrolled, 'daemon_start_txt')
        self.msd_dstart_return_txt = xrc.XRCCTRL(
            self.msd_scrolled, 'dstart_return_txt')
        self.msd_daemon_stop_txt = xrc.XRCCTRL(
            self.msd_scrolled, 'daemon_stop_txt')
        self.msd_dstop_return_txt = xrc.XRCCTRL(
            self.msd_scrolled, 'dstop_return_txt')
        self.msd_daemon_update_check_txt = xrc.XRCCTRL(
            self.msd_scrolled, 'daemon_update_check_txt')
        self.msd_ducheck_return_txt = xrc.XRCCTRL(
            self.msd_scrolled, 'ducheck_return_txt')
        self.msd_daemon_update_start_txt = xrc.XRCCTRL(
            self.msd_scrolled, 'daemon_update_start_txt')
        self.msd_dustart_return_txt = xrc.XRCCTRL(
            self.msd_scrolled, 'dustart_return_txt')
        self.msd_daemon_update_stop_txt = xrc.XRCCTRL(
            self.msd_scrolled, 'daemon_update_stop_txt')
        self.msd_dustop_return_txt = xrc.XRCCTRL(
            self.msd_scrolled, 'dustop_return_txt')
        # Buttons
        self.msd_general_save = xrc.XRCCTRL(
            self.msd_dlg, 'msd_general_save')
        self.msd_general_save.page = 'general'
        self.msd_daemon_save = xrc.XRCCTRL(
            self.msd_scrolled, 'msd_daemon_save')
        self.msd_daemon_save.page = 'daemon'
        self.msd_general_save.action = 'settings'

        # Dialog Binds
        self.msd_dlg.Bind(
            wx.EVT_BUTTON, self.update_settings,
            id=xrc.XRCID('msd_general_save'))
        self.msd_dlg.Bind(
            wx.EVT_BUTTON, self.general_reset,
            id=xrc.XRCID('msd_general_reset'))
        self.msd_dlg.Bind(
            wx.EVT_BUTTON, self.update_settings,
            id=xrc.XRCID('msd_daemon_save'))
        self.msd_dlg.Bind(
            wx.EVT_BUTTON, self.daemon_reset,
            id=xrc.XRCID('msd_daemon_reset'))
        self.msd_dlg.Bind(
            wx.EVT_BUTTON, self.daemon_help,
            id=xrc.XRCID('msd_daemon_help'))
        self.msd_dlg.Bind(wx.EVT_CLOSE, self.dlg_closer)
        #self.msd_scrolled.Bind(wx.EVT_PAINT, self.temp)
        self.msd_dlg.Bind(wx.EVT_MOUSEWHEEL, self.daemon_scroll)
        self.msd_scrolled.SetVirtualSize((500,400))
        self.msd_scrolled.SetScrollRate(20,20)
        self.msd_dlg.SetSize((500,400))
        self.msd_dlg.SetMinSize((500,400))
        self.msd_dlg.Show()
        self.settings_size_fix(wx.EVT_PAINT)

    def daemon_scroll(self, event):
        if self.msd_nb.GetSelection() == 1:
            # Allow scrolling only if on scrolled window tab
            amt = event.GetWheelRotation()
            units = amt/(-(event.GetWheelDelta()))
            self.msd_scrolled.ScrollLines(units*3)

    def settings_size_fix(self, event):
        # For some messed up reason, setting the size before calling .show()
        # does not work! However, setting the size after an event works!
        # Hence this function is called as a dummy event after show().
        self.msd_scrolled.SetVirtualSize((500,400))
        self.msd_dlg.SetSize((500,400))
        self.msd_scrolled.Refresh()
        self.msd_dlg.Refresh()

    def update_settings(self, event):
        page = str(event.GetEventObject().page)
        if page == 'general':
            # Check for proper format
            message = ''
            status_ssh_maxtime = self.msd_sshstatus_time.GetValue()
            status_rcon_maxtime = self.msd_rconstatus_time.GetValue()
            max_rcon_attempts = self.msd_max_rcon_attempts.GetValue()
            if status_ssh_maxtime.isdigit():
                status_ssh_maxtime = int(status_ssh_maxtime)
                self.msd_statusssh_txt.SetForegroundColour('Black')
            else:
                message += '\n* SSH Frequency must contain only numbers.'
                self.msd_statusssh_txt.SetForegroundColour('Red')
            if status_rcon_maxtime.isdigit():
                status_rcon_maxtime = int(status_rcon_maxtime)
                self.msd_statusrcon_txt.SetForegroundColour('Black')
            else:
                message += '\n* RCON Frequency must contain only numbers.'
                self.msd_statusrcon_txt.SetForegroundColour('Red')
            if max_rcon_attempts.isdigit():
                max_rcon_attempts = int(max_rcon_attempts)
                self.max_rcon_attempts_txt.SetForegroundColour('Black')
            else:
                message += '\n* Max RCON must contain only numbers.'
                self.max_rcon_attempts_txt.SetForegroundColour('Red')
            message = message[1:]
            if len(message) > 0:
                warning_dlg = wx.MessageDialog(
                    self.frame, message, 'Alert!', wx.OK|wx.ICON_WARNING)
                warning_dlg.ShowModal()
                warning_dlg.Destroy()
                self.msd_dlg.Refresh()
            else:
                # Begin saving into variable and database
                if self.msd_enable_sshstatus.GetValue() == True:
                    self.settings['enable_status_ssh'] = 1
                    self.menubar.Check(xrc.XRCID('enable_status_ssh'), True)
                else:
                    self.settings['enable_status_ssh'] = 0
                    self.menubar.Check(xrc.XRCID('enable_status_ssh'), False)
                if self.msd_enable_rconstatus.GetValue() == True:
                    self.settings['enable_status_rcon'] = 1
                    self.menubar.Check(
                        xrc.XRCID('enable_status_rcon'), True)
                else:
                    self.settings['enable_status_rcon'] = 0
                    self.menubar.Check(xrc.XRCID('enable_status_rcon'), False)
                if self.msd_enable_debuglog.GetValue() == True:
                    self.settings['enable_debuglog'] = 1
                else:
                    self.settings['enable_debuglog'] = 0
                self.settings['status_ssh_maxtime'] = status_ssh_maxtime
                self.settings['status_rcon_maxtime'] = status_rcon_maxtime
                self.settings['max_rcon_attempts'] = max_rcon_attempts
                self.sql.connect()
                self.sql.c.execute(
                    'UPDATE config SET enable_status_ssh = ?, '
                    'enable_status_rcon = ?, status_ssh_maxtime = ?, '
                    'status_rcon_maxtime = ?, max_rcon_attempts = ?, '
                    'enable_debuglog = ? WHERE UID = ?',
                    (self.settings['enable_status_ssh'],
                     self.settings['enable_status_rcon'],
                     self.settings['status_ssh_maxtime'],
                     self.settings['status_rcon_maxtime'],
                     self.settings['max_rcon_attempts'],
                     self.settings['enable_debuglog'], str(self.user['UID'])))
                self.sql.close(1)
                text = 'General Settings saved successfully.'
                self.output(text, 'Settings')
                self.msd_dlg.Refresh()
        elif page == 'daemon':
            # Check for proper data
            message = ''
            daemon_check = self.msd_daemon_check.GetValue()
            dcheck_return = self.msd_dcheck_return.GetValue()
            daemon_start = self.msd_daemon_start.GetValue()
            dstart_return = self.msd_dstart_return.GetValue()
            daemon_stop = self.msd_daemon_stop.GetValue()
            dstop_return = self.msd_dstop_return.GetValue()
            daemon_update_check = self.msd_daemon_update_check.GetValue()
            ducheck_return = self.msd_ducheck_return.GetValue()
            daemon_update_start = self.msd_daemon_update_start.GetValue()
            dustart_return = self.msd_dustart_return.GetValue()
            daemon_update_stop = self.msd_daemon_update_stop.GetValue()
            dustop_return = self.msd_dustop_return.GetValue()
            if len(daemon_check) > 0:
                self.msd_daemon_check_txt.SetForegroundColour('Black')
            else:
                self.msd_daemon_check_txt.SetForegroundColour('Red')
                message += '\n Daemon Check must contain data'
            if len(dcheck_return) > 0:
                self.msd_dcheck_return_txt.SetForegroundColour('Black')
            else:
                self.msd_dcheck_return_txt.SetForegroundColour('Red')
                message += '\n Daemon Check\'s Return must contain data'
            if len(daemon_start) > 0:
                self.msd_daemon_start_txt.SetForegroundColour('Black')
            else:
                self.msd_daemon_start_txt.SetForegroundColour('Red')
                message += '\n Daemon Start must contain data'
            if len(dstart_return) > 0:
                self.msd_dstart_return_txt.SetForegroundColour('Black')
            else:
                self.msd_dstart_return_txt.SetForegroundColour('Red')
                message += '\n Daemon Start\'s Return must contain data'
            if len(daemon_stop) > 0:
                self.msd_daemon_stop_txt.SetForegroundColour('Black')
            else:
                self.msd_daemon_stop_txt.SetForegroundColour('Red')
                message += '\n Daemon Stop must contain data'
            if len(dstop_return) > 0:
                self.msd_dstop_return_txt.SetForegroundColour('Black')
            else:
                self.msd_dstop_return_txt.SetForegroundColour('Red')
                message += '\n Daemon Stop\'s Return must contain data'
            if len(daemon_update_check) > 0:
                self.msd_daemon_update_check_txt.SetForegroundColour('Black')
            else:
                self.msd_daemon_update_check_txt.SetForegroundColour('Red')
                message += '\n Daemon Update Check must contain data'
            if len(ducheck_return) > 0:
                self.msd_ducheck_return_txt.SetForegroundColour('Black')
            else:
                self.msd_ducheck_return_txt.SetForegroundColour('Red')
                message += '\n Daemon Update Check\'s Return must contain data'
            if len(daemon_update_start) > 0:
                self.msd_daemon_update_start_txt.SetForegroundColour('Black')
            else:
                self.msd_daemon_update_start_txt.SetForegroundColour('Red')
                message += '\n Daemon Update Start must contain data'
            if len(dustart_return) > 0:
                self.msd_dustart_return_txt.SetForegroundColour('Black')
            else:
                self.msd_dustart_return_txt.SetForegroundColour('Red')
                message += '\n Daemon Update Start\'s Return must contain data'
            if len(daemon_update_stop) > 0:
                self.msd_daemon_update_stop_txt.SetForegroundColour('Black')
            else:
                self.msd_daemon_update_stop_txt.SetForegroundColour('Red')
                message += '\n Daemon Update Stop must contain data'
            if len(dustop_return) > 0:
                self.msd_dustop_return_txt.SetForegroundColour('Black')
            else:
                self.msd_dustop_return_txt.SetForegroundColour('Red')
                message += '\n Daemon Update Stop\'s Return must contain data'
            message = message[1:]
            if len(message) > 0:
                warning_dlg = wx.MessageDialog(
                    self.frame, message, 'Alert!', wx.OK|wx.ICON_WARNING)
                warning_dlg.ShowModal()
                warning_dlg.Destroy()
                self.msd_dlg.Refresh()
            else:
                # Begin saving into variable and database
                self.settings['daemon_check'] = daemon_check
                self.settings['dcheck_return'] = dcheck_return
                self.settings['daemon_start'] = daemon_start
                self.settings['dstart_return'] = dstart_return
                self.settings['daemon_stop'] = daemon_stop
                self.settings['dstop_return'] = dstop_return
                self.settings['daemon_update_check'] = daemon_update_check
                self.settings['ducheck_return'] = ducheck_return
                self.settings['daemon_update_start'] = daemon_update_start
                self.settings['dustart_return'] = dustart_return
                self.settings['daemon_update_stop'] = daemon_update_stop
                self.settings['dustop_return'] = dustop_return
                self.sql.connect()
                self.sql.c.execute(
                    'UPDATE config SET daemon_check = ?, '
                    'dcheck_return = ?, daemon_start = ?, '
                    'dstart_return = ?, daemon_stop = ?, '
                    'dstop_return = ?, daemon_update_check = ?, '
                    'ducheck_return = ?, daemon_update_start = ?, '
                    'dustart_return = ?, daemon_update_stop = ?, '
                    'dustop_return = ? '
                    'WHERE UID = ?',
                    (self.settings['daemon_check'],
                     self.settings['dcheck_return'],
                     self.settings['daemon_start'],
                     self.settings['dstart_return'],
                     self.settings['daemon_stop'],
                     self.settings['dstop_return'],
                     self.settings['daemon_update_check'],
                     self.settings['ducheck_return'],
                     self.settings['daemon_update_start'],
                     self.settings['dustart_return'],
                     self.settings['daemon_update_stop'],
                     self.settings['dustop_return'],
                     str(self.user['UID'])))
                self.sql.close(1)
                text = 'Daemon Settings saved successfully.'
                self.output(text, 'Settings')
                self.msd_dlg.Refresh()

    def general_reset(self, event):
        self.msd_enable_sshstatus.SetValue(False)
        self.msd_enable_rconstatus.SetValue(False)
        self.msd_sshstatus_time.Clear()
        self.msd_rconstatus_time.Clear()
        self.msd_max_rcon_attempts.Clear()
        self.msd_enable_debuglog.SetValue(False)

    def daemon_reset(self, event):
        self.msd_daemon_check.Clear()
        self.msd_daemon_start.Clear()
        self.msd_daemon_stop.Clear()
        self.msd_daemon_update_check.Clear()
        self.msd_daemon_update_start.Clear()
        self.msd_daemon_update_stop.Clear()
        self.msd_dcheck_return.Clear()
        self.msd_dstart_return.Clear()
        self.msd_dstop_return.Clear()
        self.msd_ducheck_return.Clear()
        self.msd_dustart_return.Clear()
        self.msd_dustop_return.Clear()

    def daemon_help(self, event):
        self.mnotes_dlg = self.res.LoadDialog(self.frame, 'mnotes_dlg')
        self.mnotes_help = wx.TextCtrl(
            self.mnotes_dlg, -1, style=wx.TE_MULTILINE|wx.TE_WORDWRAP)
        self.msd_daemon_check.SetMinSize((100,100))
        self.res.AttachUnknownControl(
            'mnotes_help', self.mnotes_help, self.mnotes_dlg)
        #self.mnotes_help = xrc.XRCCTRL(self.mnotes_dlg, 'mnotes_help')
        self.mnotes_help.SetValue(NOTES)
        self.mnotes_dlg.SetSize((500,350))
        self.mnotes_dlg.Show()

    def toggle_menu(self, event):
        # Make sure we're logged in first
        if self.user['UID'] == -1:
            return

        old_ssh_toggle = self.settings['enable_status_ssh']
        old_rcon_toggle = self.settings['enable_status_rcon']
        if self.mb_enable_ssh.IsChecked() == True:
            self.settings['enable_status_ssh'] = 1
            ssh_text = 'Enabled SSH Status checks'
        else:
            self.settings['enable_status_ssh'] = 0
            ssh_text = 'Disabled SSH Status checks'
        if self.mb_enable_rcon.IsChecked() == True:
            self.settings['enable_status_rcon'] = 1
            rcon_text = 'Enabled RCON Status checks'
        else:
            self.settings['enable_status_rcon'] = 0
            rcon_text = 'Disabled RCON Status checks'
        self.sql.connect()
        self.sql.c.execute(
            'UPDATE config SET enable_status_ssh = ?, '
            'enable_status_rcon = ? WHERE UID = ?',
            (self.settings['enable_status_ssh'],
             self.settings['enable_status_rcon'], str(self.user['UID'])))
        self.sql.close(1)
        if old_ssh_toggle != self.settings['enable_status_ssh']:
            self.output(ssh_text, 'Settings')
        if old_rcon_toggle != self.settings['enable_status_rcon']:
            self.output(rcon_text, 'Settings')

    def new_user(self, event):
         # Make sure we only open one of these dialogs
        for dlg in self.dialogs:
            if self.dialogs[dlg] == 1:
                return
        if self.dialogs['new_user'] == 0:
            self.dialogs['new_user'] = 1
        elif self.dialogs['new_user'] == 1:
            return

        self.mnu_dlg = self.res.LoadDialog(self.frame, 'mnu_dlg')
        self.mnu_dlg.SetWindowStyle(
            wx.DEFAULT_DIALOG_STYLE|wx.STAY_ON_TOP|wx.TAB_TRAVERSAL)
        self.mnu_username = xrc.XRCCTRL(self.mnu_dlg, 'mnu_username')
        self.mnu_username.SetFocus()
        self.mnu_password = xrc.XRCCTRL(self.mnu_dlg, 'mnu_password')
        self.mnu_sshaccess = xrc.XRCCTRL(self.mnu_dlg, 'mnu_sshaccess')
        self.mnu_rconaccess = xrc.XRCCTRL(self.mnu_dlg, 'mnu_rconaccess')
        self.mnu_passrequire1 = xrc.XRCCTRL(self.mnu_dlg, 'mnu_passrequire1')
        self.mnu_passrequire2 = xrc.XRCCTRL(self.mnu_dlg, 'mnu_passrequire2')
        self.mnu_passrequire3 = xrc.XRCCTRL(self.mnu_dlg, 'mnu_passrequire3')
        self.mnu_cancel_btn = xrc.XRCCTRL(self.mnu_dlg, 'mnu_cancel_btn')
        self.mnu_cancel_btn.dlg = 'new_user'

        # Dialog Binds
        self.mnu_dlg.Bind(
            wx.EVT_BUTTON, self.create_user, id=xrc.XRCID('mnu_ok_btn'))
        self.mnu_dlg.Bind(
            wx.EVT_BUTTON, self.dlg_closer, id=xrc.XRCID('mnu_cancel_btn'))
        self.mnu_dlg.Bind(
            wx.EVT_TEXT_ENTER, self.create_user, id=xrc.XRCID('mnu_username'))
        self.mnu_dlg.Bind(
            wx.EVT_TEXT_ENTER, self.create_user, id=xrc.XRCID('mnu_password'))
        self.mnu_dlg.Bind(
            wx.EVT_CLOSE, self.dlg_closer)
        self.mnu_dlg.Show()

    def create_user(self, event):
        # Check requirements
        new_username = self.mnu_username.GetValue()
        new_password = self.mnu_password.GetValue()
        sshaccess = '0'
        rconaccess = '0'
        check1 = 0
        check2 = 0
        check3 = 0
        self.mnu_passrequire1.SetForegroundColour('Black')
        self.mnu_passrequire2.SetForegroundColour('Black')
        self.mnu_passrequire3.SetForegroundColour('Black')
        if len(new_username) < 2 or len(new_username) > 30:
            check1 += 1
            self.mnu_passrequire1.SetForegroundColour('Red')
        if len(new_password) < 8 or len(new_password) > 30:
            check2 += 1
            self.mnu_passrequire2.SetForegroundColour('Red')
        if new_password.find(' ') != -1:
            check3 += 1
        if new_username.find(' ') != -1:
            check3 += 1
        if check3 > 0:
            self.mnu_passrequire3.SetForegroundColour('Red')
        self.mnu_dlg.Refresh()
        # Insert data
        if check1 == 0 and check2 == 0 and check3 == 0:
            if self.mnu_sshaccess.IsChecked():
                sshaccess = '1'
            if self.mnu_rconaccess.IsChecked():
                rconaccess = '1'
            self.mnu_dlg.Destroy()
            self.dialogs['new_user'] = 0
            self.sql.connect()
            # Create salted password and IV for CBC encryption
            new_password += sshaccess + rconaccess
            self.user['IV'] = (
                ''.join(random.sample(
                    string.ascii_uppercase + string.digits,16)))
            self.user['key'] = new_password
            new_password = hashlib.md5(
                str(self.user['IV']) + new_password).hexdigest()
            self.user['password'] = new_password
            # Create dummy group data
            self.new_group_name = "Servers"
            self.sql.c.execute(
                "INSERT INTO groups(name, description) VALUES(?, ?)",
                (str(self.new_group_name), "No You!"))
            newID = self.sql.c.lastrowid
            # Create new user data
            self.server_status = {}
            self.sql.c.execute(
                'INSERT INTO users(name, password, iv, grouplist, ' +
                'ssh_access, rcon_access) VALUES(?, ?, ?, ?, ?, ?)',
                (str(new_username), str(self.user['password']),
                 str(self.user['IV']), str(newID), sshaccess, rconaccess))
            self.user['UID'] = self.sql.c.lastrowid
            self.user['name'] = str(new_username)
            self.user['ssh_access'] = sshaccess
            self.user['rcon_access'] = rconaccess
            self.sql.c.execute(
                'INSERT INTO config(UID, enable_status_ssh) ' +
                'VALUES(?, ?)', (str(self.user['UID']), '1'))
            results = self.sql.c.execute(
                'SELECT * FROM config WHERE UID = ' + str(self.user['UID']))
            for row in results:
                self.settings['enable_status_ssh'] = row[1]
                self.menubar.Check(xrc.XRCID('enable_status_ssh'), True)
                self.settings['enable_status_rcon'] = row[2]
                self.menubar.Check(xrc.XRCID('enable_status_rcon'), True)
                self.settings['status_ssh_maxtime'] = row[3]
                self.settings['status_rcon_maxtime'] = row[4]
                self.settings['max_rcon_attempts'] = row[5]
                self.settings['enable_debuglog'] = row[6]
                self.settings['daemon_check'] = row[7]
                self.settings['dcheck_return'] = row[8]
                self.settings['daemon_start'] = row[9]
                self.settings['dstart_return'] = row[10]
                self.settings['daemon_stop'] = row[11]
                self.settings['dstop_return'] = row[12]
                self.settings['daemon_update_check'] = row[13]
                self.settings['ducheck_return'] = row[14]
                self.settings['daemon_update_start'] = row[15]
                self.settings['dustart_return'] = row[16]
                self.settings['daemon_update_stop'] = row[17]
                self.settings['dustop_return'] = row[18]
            self.sql.close(1)
            # Create debug log if enabled
            if self.settings['enable_debuglog'] == 1:
                self.logging = logging.getLogger('Mantib Logging')
                self.logging.setLevel(logging.DEBUG)
                handler = logging.handlers.RotatingFileHandler(
                    'mantig.log', maxBytes=10240, backupCount=0)
                fmt = logging.Formatter(fmt='%(asctime)s %(message)s')
                handler.setFormatter(fmt)
                self.logging.addHandler(handler)
            # Display data
            text = 'New user created/opened.'
            self.output(text, 'New User')
            self.reload_groups(wx.EVT_BUTTON)
            self.enable_tooblar(enable=False, new=True)

    def sign_in(self, event):
        # Make sure we only open one of these dialogs
        for dlg in self.dialogs:
            if self.dialogs[dlg] == 1:
                return
        if self.dialogs['sign_in'] == 0:
            self.dialogs['sign_in'] = 1
        elif self.dialogs['sign_in'] == 1:
            return

        self.msi_dlg = self.res.LoadDialog(None, 'msi_dlg')
        self.msi_dlg.SetWindowStyle(
            wx.DEFAULT_DIALOG_STYLE|wx.TAB_TRAVERSAL)
        self.msi_username = xrc.XRCCTRL(self.msi_dlg, 'msi_username')
        self.msi_username.SetFocus()
        self.msi_password = xrc.XRCCTRL(self.msi_dlg, 'msi_password')
        #self.msi_username.SetValue('root')
        self.msi_cancel_btn = xrc.XRCCTRL(self.msi_dlg, 'msi_cancel_btn')
        self.msi_cancel_btn.dlg = 'sign_in'
        self.msi_dlg.Bind(
            wx.EVT_BUTTON, self.open_user, id=xrc.XRCID('msi_ok_btn'))
        self.msi_dlg.Bind(
            wx.EVT_BUTTON, self.dlg_closer, id=xrc.XRCID('msi_cancel_btn'))
        self.msi_dlg.Bind(
            wx.EVT_TEXT_ENTER, self.open_user, id=xrc.XRCID('msi_username'))
        self.msi_dlg.Bind(
            wx.EVT_TEXT_ENTER, self.open_user, id=xrc.XRCID('msi_password'))
        self.msi_dlg.Bind(wx.EVT_CLOSE, self.dlg_closer)
        self.msi_dlg.Show()

    def open_user(self, event):
        user_info = {}
        check_login = 0 # Used as a check for sql user/pass success
        check_servers = 0 # Used as a check for any servers available
        match_username = self.msi_username.GetValue()
        match_password = self.msi_password.GetValue()
        self.sql.connect()
        # First find matching username and get it's salted key
        results = self.sql.c.execute(
            'SELECT * FROM users WHERE name = "' + str(match_username) + '"')
        for row in results:
            user_info['ID'] = row[0]
            user_info['name'] = row[1]
            user_info['password'] = row[2]
            user_info['IV'] = row[3]
            user_info['grouplist'] = row[4]
            user_info['ssh_access'] = str(row[5])
            user_info['rcon_access'] = str(row[6])
            check_login = 1
        if check_login == 0:
            warning_dlg = wx.MessageDialog(
                self.frame, 'Could not find matching user!', 'Alert!',
                wx.OK|wx.ICON_EXCLAMATION)
            warning_dlg.ShowModal()
            warning_dlg.Destroy()
            self.sql.close()
            return
        else:
            # Reset check for password check next
            check_login = 0
        match_password += user_info['ssh_access'] + user_info['rcon_access']
        user_key = match_password # unencrypted pass
        match_password = hashlib.md5(
            user_info['IV'] + match_password).hexdigest()
        if user_info['password'] == match_password:
            self.group_order = user_info['grouplist']
            self.user['key'] = user_key
            self.user['IV'] = user_info['IV']
            self.user['password'] = user_info['password']
            self.user['name'] = user_info['name']
            self.user['UID'] = user_info['ID']
            self.user['ssh_access'] = user_info['ssh_access']
            self.user['rcon_access'] = user_info['rcon_access']
            check_login = 1
        # Don't continue if we failed to login
        if check_login != 1:
            warning_dlg = wx.MessageDialog(
                self.frame, 'Wrong password!', 'Alert!',
                wx.OK|wx.ICON_EXCLAMATION)
            warning_dlg.ShowModal()
            warning_dlg.Destroy()
            self.sql.close()
            return
        # Get settings
        results = self.sql.c.execute(
            'SELECT * FROM config WHERE UID = ' + str(self.user['UID']))
        for row in results:
            self.settings['enable_status_ssh'] = row[1]
            if row[1] == 1:
                self.menubar.Check(xrc.XRCID('enable_status_ssh'), True)
            else:
                self.menubar.Check(xrc.XRCID('enable_status_ssh'), False)
            self.settings['enable_status_rcon'] = row[2]
            if row[2] == 1:
                self.menubar.Check(xrc.XRCID('enable_status_rcon'), True)
            else:
                self.menubar.Check(xrc.XRCID('enable_status_rcon'), False)
            self.settings['status_ssh_maxtime'] = row[3]
            self.settings['status_rcon_maxtime'] = row[4]
            self.settings['max_rcon_attempts'] = row[5]
            self.settings['enable_debuglog'] = row[6]
            self.settings['daemon_check'] = row[7]
            self.settings['dcheck_return'] = row[8]
            self.settings['daemon_start'] = row[9]
            self.settings['dstart_return'] = row[10]
            self.settings['daemon_stop'] = row[11]
            self.settings['dstop_return'] = row[12]
            self.settings['daemon_update_check'] = row[13]
            self.settings['ducheck_return'] = row[14]
            self.settings['daemon_update_start'] = row[15]
            self.settings['dustart_return'] = row[16]
            self.settings['daemon_update_stop'] = row[17]
            self.settings['dustop_return'] = row[18]
        self.sql.close()
        # Create debug log if enabled
        if self.settings['enable_debuglog'] == 1:
            self.logging = logging.getLogger('Mantib Logging')
            self.logging.setLevel(logging.DEBUG)
            handler = logging.handlers.RotatingFileHandler(
                'mantig.log', maxBytes=10240, backupCount=0)
            fmt = logging.Formatter(fmt='%(asctime)s %(message)s')
            handler.setFormatter(fmt)
            self.logging.addHandler(handler)
        # Log the action
        text = 'Successful login, user opened.'
        self.output(text, 'Open')
        # Reset/Load notebook, ultimatelistctrl, and toolbar
        self.reload_groups(wx.EVT_BUTTON)
        self.msi_dlg.Destroy()
        self.dialogs['sign_in'] = 0

    def enable_tooblar(self, enable=True, new=False):
        if enable == True:
            if (self.user['ssh_access'] == '0' or
                self.user['rcon_access'] == '0'):
                self.mb_group_export.Enable(False)
                self.mb_group_import.Enable(True)
            else:
                self.mb_group_export.Enable(True)
                self.mb_group_import.Enable(True)
            self.toolbar.EnableTool(10, True) # Group Add
            self.toolbar.EnableTool(20, True) # Group Edit
            self.toolbar.EnableTool(30, True) # Group Delete
            self.toolbar.EnableTool(40, True) # Reload Groups
            self.toolbar.EnableTool(50, True) # New Server
            self.toolbar.EnableTool(60, True) # Server Edit
            if (self.user['ssh_access'] == '1' or
                self.user['rcon_access'] == '1'):
                self.toolbar.EnableTool(70, True) # Server Key
            else:
                self.toolbar.EnableTool(70, False) # Server Key
            self.toolbar.EnableTool(80, True) # Server Delete
            self.toolbar.EnableTool(90, True) # Daemon Start
            self.toolbar.EnableTool(100, True) # Daemon Stop
            self.toolbar.EnableTool(110, True) # Daemon Update Start
            self.toolbar.EnableTool(120, True) # Daemon Update Stop
            self.toolbar.EnableTool(130, True) # Daemon Update Check
            if self.user['ssh_access'] == '1':
                self.toolbar.EnableTool(140, True) # SSH Terminal
            else:
                self.toolbar.EnableTool(140, False) # SSH Terminal
            if self.user['rcon_access'] == '1':
                self.toolbar.EnableTool(150, True) # RCON Terminal
            else:
                self.toolbar.EnableTool(150, False) # RCON Terminal
        else:
            self.mb_group_export.Enable(False)
            self.mb_group_import.Enable(True)
            self.toolbar.EnableTool(10, False) # Group Add
            self.toolbar.EnableTool(20, False) # Group Edit
            self.toolbar.EnableTool(30, False) # Group Delete
            self.toolbar.EnableTool(40, False) # Reload Groups
            if new == True:
                self.toolbar.EnableTool(50, True) # New Server
            else:
                self.toolbar.EnableTool(50, False) # New Server
            self.toolbar.EnableTool(60, False) # Server Edit
            self.toolbar.EnableTool(70, False) # Server Key
            self.toolbar.EnableTool(80, False) # Server Delete
            self.toolbar.EnableTool(90, False) # Daemon Start
            self.toolbar.EnableTool(100, False) # Daemon Stop
            self.toolbar.EnableTool(110, False) # Daemon Update Start
            self.toolbar.EnableTool(120, False) # Daemon Update Stop
            self.toolbar.EnableTool(130, False) # Daemon Update Check
            self.toolbar.EnableTool(140, False) # SSH Terminal
            self.toolbar.EnableTool(150, False) # RCON Terminal

    def group_add(self, event):
        groupadd_dlg = wx.TextEntryDialog(
            self.frame, 'Group Name?', 'Group Add', 'Servers')
        if groupadd_dlg.ShowModal() == wx.ID_OK:
            self.new_group_name = groupadd_dlg.GetValue()
            if len(self.new_group_name) < 2 or len(self.new_group_name) > 32:
                warning_dlg = wx.MessageDialog(
                    self.frame, 'Group name must be between 2 to 32 '
                    'characters long!', 'Alert!', wx.OK|wx.ICON_EXCLAMATION)
                warning_dlg.ShowModal()
                warning_dlg.Destroy()
                groupadd_dlg.Destroy()
            else:
                self.sql.connect()
                self.sql.c.execute(
                    "INSERT INTO groups(name, description) VALUES(?, ?)",
                    (str(self.new_group_name), "No You!"))
                newID = self.sql.c.lastrowid
                self.group_order += ',' + str(newID)
                self.add_ulc_columns(newID, self.new_group_name)
                self.sql.c.execute(
                    'UPDATE users SET grouplist = "' + self.group_order +
                    '" WHERE ID = ' + str(self.user['UID']))
                self.sql.close(1)
                groupadd_dlg.Destroy()
                text = 'New group "' + self.new_group_name + '" created.'
                self.output(text, 'Group')

    def group_edit(self, event):
        # Get currently selected group
        group_name = self.server_nb.GetPageText(self.server_nb.GetSelection())
        for key in self.groups:
            if self.groups[key] == group_name:
                groupID = key
                break

        # Prompt for new name and rename it
        rng_dlg = wx.TextEntryDialog(
            self.frame,
            'What should the new group name for ' + group_name + ' be?',
            'Rename Group', str(group_name))
        if rng_dlg.ShowModal() == wx.ID_OK:
            new_name = rng_dlg.GetValue()
            if len(new_name) < 2 or len(new_name) > 32:
                warning_dlg = wx.MessageDialog(
                    self.frame, 'Group name must be between 2 to 32 '
                    'characters long!', 'Alert!', wx.OK|wx.ICON_EXCLAMATION)
                warning_dlg.ShowModal()
                warning_dlg.Destroy()
            else:
                self.sql.connect()
                self.sql.c.execute(
                    'UPDATE groups SET name = "' + str(new_name) + '" WHERE ' +
                    'ID = "' + str(groupID) + '"')
                self.sql.close(1)
                rng_dlg.Destroy()
                self.server_nb.SetPageText(
                    self.server_nb.GetSelection(), new_name)
                text = (
                    'Group name "' + self.groups[str(groupID)] +
                    '" changed to "' + new_name + '".')
                self.output(text, 'Group')
                self.groups[str(groupID)] = new_name
        else:
            rng_dlg.Destroy()

    def group_delete(self, event):
        # Check if we have more than one group
        if len(self.groups) < 2:
            warning_dlg = wx.MessageDialog(
                self.frame, 'You can not delete your last group!', 'WARNING!',
                wx.OK|wx.ICON_STOP)
            warning_dlg.ShowModal()
            warning_dlg.Destroy()
            return

        # Build group list
        groups = []
        for groupID in self.groups:
            groups.append(self.groups[groupID])
        dgp_dlg = wx.SingleChoiceDialog(
            self.frame, 'Select a group to delete.', 'Delete Group',
            groups, wx.CHOICEDLG_STYLE)
        if dgp_dlg.ShowModal() == wx.ID_OK:
            old_group_name = groups[dgp_dlg.GetSelection()]
            for groupID in self.groups:
                if old_group_name == self.groups[groupID]:
                    GID = groupID # The ID of group to delete
                    break
            dgp_dlg.Destroy()

            # Find if any servers to migrate
            migrate_servers = {}
            self.sql.connect()
            results = self.sql.c.execute(
                'SELECT ID, name FROM servers WHERE GID = "' + str(GID) + '"')
            for row in results:
                migrate_servers[str(row[0])] = row[1]
            # If we have servers to migrate prompt for destination group
            if len(migrate_servers) > 0:
                group_total = len(groups) - 1
                # Only prompt if there is more than one to choose from
                if group_total > 1:
                    groups = []
                    for groupID in self.groups:
                        if GID != groupID:
                            groups.append(self.groups[groupID])
                    dgp_dlg = wx.SingleChoiceDialog(
                        self.frame, 'Which group do you want to ' +
                        'migrate servers to?', 'Server Migration',
                        groups, wx.CHOICEDLG_STYLE)
                    if dgp_dlg.ShowModal() == wx.ID_OK:
                        new_group_name = groups[dgp_dlg.GetSelection()]
                        for groupID in self.groups:
                            if new_group_name == self.groups[groupID]:
                                newGID = groupID # The destination group ID
                                break
                        dgp_dlg.Destroy()
                    else:
                        dgp_dlg.Destroy()
                        return
                else:
                    for groupID in self.groups:
                        if self.groups[groupID] != old_group_name:
                            newGID = groupID

                # Begin server migration
                for SID in migrate_servers:
                    self.sql.c.execute(
                        'UPDATE servers SET GID = "' + str(newGID) +
                        '" WHERE ID = "' + str(SID) + '"')
                    self.server_status[migrate_servers[SID]]['GID'] = newGID
                    self.add_ulc_data([newGID, migrate_servers[SID]])
                text = (
                    'Group "' + old_group_name + '" servers migrated to "' +
                    str(self.groups[newGID]) + '".')
                self.output(text, 'Group')

            # Delete the group
            self.sql.c.execute(
                'DELETE FROM groups WHERE ID = "' + str(GID) + '"')
            groupTemp = self.group_order.split(',')
            groupTemp.remove(GID)
            self.group_order = ','.join(groupTemp)
            self.sql.c.execute(
                'UPDATE users SET grouplist = "' + str(self.group_order) +
                '" WHERE ID = "' + str(self.user['UID']) + '"')
            self.sql.close(1)
            total_pages = self.server_nb.GetPageCount()
            count = 0
            while count < total_pages:
                page_name = self.server_nb.GetPageText(count)
                if old_group_name == page_name:
                    self.server_ulc[str(GID)].Freeze()
                    self.server_ulc[str(GID)].ClearAll()
                    self.server_ulc[str(GID)].Thaw()
                    self.server_ulc[str(GID)].Update()
                    del self.server_ulc[str(GID)]
                    self.server_nb.DeletePage(count)
                    self.sql.connect()
                    results = self.sql.c.execute(
                        'SELECT grouplist FROM users WHERE ID = "' +
                        str(self.user['UID']) + '"')
                    for row in results:
                        self.group_order = row[0]
                    order = self.group_order.split(',')
                    self.groups.clear()
                    for groupID in order:
                        results = self.sql.c.execute(
                            'SELECT * FROM groups WHERE ID = "' +
                            str(groupID) + '"')
                        for row in results:
                            self.groups[str(groupID)] = row[1]
                    self.sql.close()
                    break
                else:
                    count += 1

            # Inform user the action is completed.
            text = 'Group "' + old_group_name + '" deleted.'
            self.output(text, 'Group')
        else:
            dgp_dlg.Destroy()
            return

    def group_import(self, event):
        # Open CSV file
        open_dlg = wx.FileDialog(
            self.frame, message='Choose a file',
            defaultDir=os.getcwd(),
            defaultFile='',
            wildcard='CSV files (*.csv)|*.csv|All files (*.*)|*.*',
            style=wx.FD_OPEN|wx.FD_CHANGE_DIR)
        if open_dlg.ShowModal() == wx.ID_OK:
            f = open_dlg.GetPath()
            open_dlg.Destroy()
        else:
            open_dlg.Destroy()
            return

        # Choose existing group
        groups = []
        for groupID in self.groups:
            groups.append(self.groups[groupID])
        igp_dlg = wx.SingleChoiceDialog(
            self.frame, 'Select a group to import into.', 'Group Import',
            groups, wx.CHOICEDLG_STYLE)
        if igp_dlg.ShowModal() == wx.ID_OK:
            group_name = groups[igp_dlg.GetSelection()]
            for groupID in self.groups:
                if group_name == self.groups[groupID]:
                    GID = groupID # The ID of group to delete
                    break
            igp_dlg.Destroy()
        else:
            igp_dlg.Destroy()
            return

        # Encrypt passwords and save new data
        renamed = 0 # To inform user if some servers needed renaming
        reader = csv.reader(open(f, 'rb'))
        for row in reader:
            if len(row) == 7:
                cipher_key = self.user['key']
                name = str(row[0])
                ipaddress = str(row[1])
                ssh_user = str(row[2])
                ssh_pass = str(row[3])
                ssh_port = str(row[4])
                rcon_pass = str(row[5])
                rcon_port = str(row[6])
                while len(cipher_key) < 32:
                    cipher_key += ' '
                while len(ssh_pass) < 32:
                    ssh_pass += ' '
                while len(rcon_pass) < 32:
                    rcon_pass += ' '
                cipher_obj = AES.new(cipher_key, AES.MODE_CBC, self.user['IV'])
                ssh_pass = cipher_obj.encrypt(ssh_pass).encode('hex')
                rcon_pass = cipher_obj.encrypt(rcon_pass).encode('hex')
                self.sql.connect()
                # Make sure name is unique
                temp = name
                while True:
                    count = 0
                    results = self.sql.c.execute(
                        'SELECT name FROM servers WHERE name = "' + temp + '"')
                    for row in results:
                        count = 1
                    if count == 1:
                        temp = (
                            ''.join(random.sample(
                                string.ascii_uppercase + string.digits,16)))
                        renamed = 1
                    else:
                        name = temp
                        break
                self.sql.c.execute(
                    'INSERT INTO servers(name, ipaddress, GID, ssh_username, '
                    'ssh_password, ssh_port, rcon_password, rcon_port) '
                    'VALUES(?, ?, ?, ?, ?, ?, ?, ?)',
                    (name, ipaddress, GID, ssh_user, ssh_pass, ssh_port,
                     rcon_pass, rcon_port))
                self.sql.close(1)
            else:
                text = 'File seems invalid. Stopping before further corruption.'
                self.output(text, 'Group Import')
                return
        if renamed == 1:
            self.output('Some names needed renaming!', 'Group Import')
        text = ('Data successfully imported into "' +
                str(group_name) + '" group.')
        self.output(text, 'Group Import')
        self.reload_groups(wx.EVT_TOOL)

    def group_export(self, event):
        # Load group selection dialog
        groups = []
        for groupID in self.groups:
            groups.append(self.groups[groupID])
        egp_dlg = wx.SingleChoiceDialog(
            self.frame, 'Select a group to export.', 'Group Export',
            groups, wx.CHOICEDLG_STYLE)
        if egp_dlg.ShowModal() == wx.ID_OK:
            group_name = groups[egp_dlg.GetSelection()]
            for groupID in self.groups:
                if group_name == self.groups[groupID]:
                    GID = groupID # The ID of group to delete
                    break
            egp_dlg.Destroy()
        else:
            egp_dlg.Destroy()
            return

        # Get servers if any
        self.sql.connect()
        count = 0
        servers = []
        results = self.sql.c.execute(
            'SELECT * FROM servers WHERE GID = "' + str(GID) + '"')
        for row in results:
            count += 1
            info = []
            info.append(row[1]) # name
            info.append(row[2]) # ipaddress
            #info.append(row[3]) # GID
            info.append(row[4]) # ssh_username
            info.append(row[5]) # ssh_password
            info.append(row[6]) # ssh_port
            info.append(row[7]) # rcon_password
            info.append(row[8]) # rcon_port
            servers.append(info)
        self.sql.close()
        if count == 0:
            self.output(
                'There are no servers in this group to export.', 'Group Export')
            return

        # Save details as a CSV file
        save_dlg = wx.FileDialog(
            self.frame, message='Save file as...',
            defaultDir=os.getcwd(),
            defaultFile='',
            wildcard='CSV files (*.csv)|*.csv|All files (*.*)|*.*',
            style=wx.FD_SAVE)
        if save_dlg.ShowModal() == wx.ID_OK:
            f = save_dlg.GetPath()
            writer = csv.writer(open(f, 'wb'))
            for data in servers:
                unecrypted = data
                passwords = self.decrypt_pass(data[0])
                unecrypted[3] = passwords['ssh_pass']
                unecrypted[5] = passwords['rcon_pass']
                writer.writerow(unecrypted)
            text = 'Group "' + group_name + '" successfully exported.'
            self.output(text, 'Group Export')
        save_dlg.Destroy()

    def reload_groups(self, event):
        # Reset notebook/ulc
        self.server_nb.DeleteAllPages()
        self.server_ulc.clear()

        # Initialize self.groups, self.group_order, and self.server_status
        self.sql.connect()
        results = self.sql.c.execute(
            'SELECT grouplist FROM users WHERE ID = "' +
            str(self.user['UID']) + '"')
        for row in results:
            self.group_order = row[0]
        order = self.group_order.split(',')
        self.groups.clear()
        for groupID in order:
            results = self.sql.c.execute(
                'SELECT * FROM groups WHERE ID = "' + str(groupID) + '"')
            for row in results:
                self.groups[str(groupID)] = row[1]
        self.timer_stats['init'] = 0
        check_servers = 0 # Used as a check for any servers available
        for GID in self.groups:
            results = self.sql.c.execute(
                'SELECT name, ipaddress, ssh_port, rcon_password, rcon_port ' +
                'FROM servers WHERE GID = "' + str(GID) + '"')
            for row in results:
                self.server_status[row[0]] = {}
                self.server_status[row[0]]['checking'] = ''
                self.server_status[row[0]]['GID'] = GID
                self.server_status[row[0]]['ipaddress'] = row[1]
                self.server_status[row[0]]['ssh_port'] = row[2]
                self.server_status[row[0]]['ssh_status'] = 'N/A'
                self.server_status[row[0]]['rcon_port'] = row[4]
                self.server_status[row[0]]['rcon_status'] = 'N/A'
                self.server_status[row[0]]['player_status'] = 'N/A'
                self.server_status[row[0]]['rcon_attempts'] = 0
                self.server_status[row[0]]['map'] = 'N/A'
                self.server_status[row[0]]['version'] = 'N/A'
                check_servers = 1
        self.sql.close()
        # If we have servers, enable entire toolbar
        if check_servers == 1:
            self.enable_tooblar(True)
        else:
            self.enable_tooblar(enable=False, new=True)
        # Get settings
        for server_name in self.server_status:
            passwords = self.decrypt_pass(server_name)
            self.server_status[server_name]['rcon_password'] = (
                passwords['rcon_pass'])

        # Load groups
        for groupID in order:
            self.add_ulc_columns(groupID, self.groups[groupID], False)
            self.sql.connect()
            results = self.sql.c.execute(
                'SELECT * FROM servers WHERE GID = ' + str(groupID))
            for row in results:
                self.add_ulc_data([groupID, row[1]])
            self.sql.close()

        # Log the action
        text = 'Groups have been reloaded.'
        self.output(text, 'Group')

    def server_add(self, event):
        # Make sure we only open one of these dialogs
        for dlg in self.dialogs:
            if self.dialogs[dlg] == 1:
                return
        if self.dialogs['new_server'] == 0:
            self.dialogs['new_server'] = 1
        elif self.dialogs['new_server'] == 1:
            return

        self.mns_dlg = self.res.LoadDialog(None, 'mns_dlg')
        self.mns_dlg.SetWindowStyle(
            wx.DEFAULT_DIALOG_STYLE|wx.TAB_TRAVERSAL)
        self.mns_name = xrc.XRCCTRL(self.mns_dlg, 'mns_name')
        self.mns_name.SetFocus()
        self.mns_ipaddress = xrc.XRCCTRL(self.mns_dlg, 'mns_ipaddress')
        self.mns_group = xrc.XRCCTRL(self.mns_dlg, 'mns_group')
        self.mns_group.Clear()
        self.sql.connect()
        results = self.sql.c.execute('SELECT name FROM groups')
        for row in results:
            self.mns_group.Append(row[0])
        self.sql.close()
        self.mns_group.SetSelection(0)
        self.mns_ssh_user = xrc.XRCCTRL(self.mns_dlg, 'mns_ssh_user')
        self.mns_ssh_pass = xrc.XRCCTRL(self.mns_dlg, 'mns_ssh_pass')
        self.mns_ssh_port = xrc.XRCCTRL(self.mns_dlg, 'mns_ssh_port')
        self.mns_rcon_pass = xrc.XRCCTRL(self.mns_dlg, 'mns_rcon_pass')
        self.mns_rcon_port = xrc.XRCCTRL(self.mns_dlg, 'mns_rcon_port')
        self.mns_name_txt = xrc.XRCCTRL(self.mns_dlg, 'mns_name_txt')
        self.mns_ipaddress_txt = xrc.XRCCTRL(self.mns_dlg, 'mns_ipaddress_txt')
        self.mns_ssh_user_txt = xrc.XRCCTRL(self.mns_dlg, 'mns_ssh_user_txt')
        self.mns_ssh_pass_txt = xrc.XRCCTRL(self.mns_dlg, 'mns_ssh_pass_txt')
        self.mns_ssh_port_txt = xrc.XRCCTRL(self.mns_dlg, 'mns_ssh_port_txt')
        self.mns_rcon_pass_txt = xrc.XRCCTRL(self.mns_dlg, 'mns_rcon_pass_txt')
        self.mns_rcon_port_txt = xrc.XRCCTRL(self.mns_dlg, 'mns_rcon_port_txt')
        self.mns_ok_btn = xrc.XRCCTRL(self.mns_dlg, 'mns_ok_btn')
        self.mns_ok_btn.dlg = 'new_server'
        self.mns_cancel_btn = xrc.XRCCTRL(self.mns_dlg, 'mns_cancel_btn')
        self.mns_cancel_btn.dlg = 'new_server'
        self.mns_dlg.Bind(
            wx.EVT_BUTTON, self.create_server, id=xrc.XRCID('mns_ok_btn'))
        #self.mns_dlg.Bind(
            #wx.EVT_TEXT_ENTER, self.create_server, id=xrc.XRCID('mns_name'))
        #self.mns_dlg.Bind(
            #wx.EVT_TEXT_ENTER, self.create_server,
            #id=xrc.XRCID('mns_ipaddress'))
        #self.mns_dlg.Bind(
            #wx.EVT_TEXT_ENTER, self.create_server, id=xrc.XRCID('mns_ssh_user'))
        #self.mns_dlg.Bind(
            #wx.EVT_TEXT_ENTER, self.create_server, id=xrc.XRCID('mns_ssh_pass'))
        #self.mns_dlg.Bind(
            #wx.EVT_TEXT_ENTER, self.create_server, id=xrc.XRCID('mns_ssh_port'))
        #self.mns_dlg.Bind(
            #wx.EVT_TEXT_ENTER, self.create_server,
            #id=xrc.XRCID('mns_rcon_pass'))
        #self.mns_dlg.Bind(
            #wx.EVT_TEXT_ENTER, self.create_server,
            #id=xrc.XRCID('mns_rcon_port'))
        self.mns_dlg.Bind(
            wx.EVT_BUTTON, self.dlg_closer, id=xrc.XRCID('mns_cancel_btn'))
        self.mns_dlg.Bind(wx.EVT_CLOSE, self.dlg_closer)
        self.mns_dlg.Show()

    def create_server(self, event):
        # Which Dialog (new or editing?)
        action = event.GetEventObject().dlg
        if action == 'new_server':
            name_txt = self.mns_name_txt
            ipaddress_txt = self.mns_ipaddress_txt
            ssh_user_txt = self.mns_ssh_user_txt
            ssh_pass_txt = self.mns_ssh_pass_txt
            ssh_port_txt = self.mns_ssh_port_txt
            rcon_pass_txt = self.mns_rcon_pass_txt
            rcon_port_txt = self.mns_rcon_port_txt
            name_ctrl = self.mns_name
            ipaddress_ctrl = self.mns_ipaddress
            group_ctrl = self.mns_group
            ssh_user_ctrl = self.mns_ssh_user
            ssh_pass_ctrl = self.mns_ssh_pass
            ssh_port_ctrl = self.mns_ssh_port
            rcon_pass_ctrl = self.mns_rcon_pass
            rcon_port_ctrl = self.mns_rcon_port
        elif action == 'server_edit':
            name_txt = self.mes_name_txt
            ipaddress_txt = self.mes_ipaddress_txt
            ssh_user_txt = self.mes_ssh_user_txt
            ssh_pass_txt = self.mes_ssh_pass_txt
            ssh_port_txt = self.mes_ssh_port_txt
            rcon_pass_txt = self.mes_rcon_pass_txt
            rcon_port_txt = self.mes_rcon_port_txt
            name_ctrl = self.mes_name
            ipaddress_ctrl = self.mes_ipaddress
            group_ctrl = self.mes_group
            ssh_user_ctrl = self.mes_ssh_user
            ssh_pass_ctrl = self.mes_ssh_pass
            ssh_port_ctrl = self.mes_ssh_port
            rcon_pass_ctrl = self.mes_rcon_pass
            rcon_port_ctrl = self.mes_rcon_port
            serverID = str(self.mes_id.GetLabel())

        # Colorize helpful hints default black and warnings red
        name_txt.SetForegroundColour('Black')
        ipaddress_txt.SetForegroundColour('Black')
        ssh_user_txt.SetForegroundColour('Black')
        ssh_pass_txt.SetForegroundColour('Black')
        ssh_port_txt.SetForegroundColour('Black')
        rcon_pass_txt.SetForegroundColour('Black')
        rcon_port_txt.SetForegroundColour('Black')
        warnings = '' # Collection of all warning notices
        name = name_ctrl.GetValue()
        ipaddress = ipaddress_ctrl.GetValue()
        group_name = group_ctrl.GetString(group_ctrl.GetSelection())
        ssh_user = ssh_user_ctrl.GetValue()
        ssh_pass = ssh_pass_ctrl.GetValue()
        ssh_port = ssh_port_ctrl.GetValue()
        rcon_pass = rcon_pass_ctrl.GetValue()
        rcon_port = rcon_port_ctrl.GetValue()
        if len(name) == 0:
            warnings += '* Name field must not be empty.\n'
            name_txt.SetForegroundColour('Red')
        if (str(name).find(' ') != -1 or str(name).find('"') != -1 or
            str(name).find("'") != -1):
            warnings += '* Name field must not contain spaces or qoutes\n'
            name_txt.SetForegroundColour('Red')
        if action != 'server_edit':
            server_list = []
            self.sql.connect()
            results = self.sql.c.execute('SELECT name FROM servers')
            for row in results:
                server_list.append(row[0])
            self.sql.close()
            for server_name in server_list:
                if str(name) == server_name:
                    warnings += '* Name already exists. Name must be unique.\n'
                    name_txt.SetForegroundColour('Red')
                    break
        try:
            socket.inet_aton(ipaddress)
        except socket.error:
            warnings += '* Invalid IP format.\n'
            ipaddress_txt.SetForegroundColour('Red')
        if len(ssh_user) == 0:
            warnings += '* SSH User field must not be empty.\n'
            ssh_user_txt.SetForegroundColour('Red')
        if len(ssh_pass) == 0:
            warnings += '* SSH Pass field must not be empty.\n'
            ssh_pass_txt.SetForegroundColour('Red')
        if ssh_port.isdigit() == False:
            warnings += '* SSH Port must be only numbers.\n'
            ssh_port_txt.SetForegroundColour('Red')
        if len(rcon_pass) == 0:
            warnings += '* RCON Pass field must not be empty.\n'
            rcon_pass_txt.SetForegroundColour('Red')
        if rcon_port.isdigit() == False:
            warnings += '* RCON Port must be only numbers.\n'
            rcon_port_txt.SetForegroundColour('Red')
        warnings = warnings[:-2]
        if len(warnings) > 0:
            warning_dlg = wx.MessageDialog(
                self.frame, warnings, 'Alert!',
                wx.OK|wx.ICON_WARNING)
            warning_dlg.ShowModal()
            warning_dlg.Destroy()
            if action == 'new_server':
                self.mns_dlg.Refresh()
            elif action == 'server_edit':
                self.mes_dlg.Refresh()
        else:
            # Passed checks, now encrypt passwords and save data
            cipher_key = self.user['key']
            while len(cipher_key) < 32:
                cipher_key += ' '
            while len(ssh_pass) < 32:
                ssh_pass += ' '
            while len(rcon_pass) < 32:
                rcon_pass += ' '
            cipher_obj = AES.new(cipher_key, AES.MODE_CBC, self.user['IV'])
            ssh_pass = cipher_obj.encrypt(ssh_pass).encode('hex')
            rcon_pass = cipher_obj.encrypt(rcon_pass).encode('hex')
            for groupID in self.groups:
                if self.groups[groupID] == group_name:
                    GID = groupID
                    break
            if action == 'new_server':
                self.sql.connect()
                self.sql.c.execute(
                    'INSERT INTO servers(name, ipaddress, GID, ssh_username, '
                    'ssh_password, ssh_port, rcon_password, rcon_port) '
                    'VALUES(?, ?, ?, ?, ?, ?, ?, ?)',
                    (name, ipaddress, GID, ssh_user, ssh_pass, ssh_port,
                     rcon_pass, rcon_port))
                self.sql.close(1)
                # Close dialog but remember to mark our toggle variable
                self.mns_dlg.Destroy()
                self.dialogs['new_server'] = 0
                # Now enable toolbar if we had no servers initially
                if len(self.server_status) < 1:
                    self.enable_tooblar()
                self.server_status[name] = {}
                self.server_status[name]['GID'] = GID
                self.server_status[name]['ipaddress'] = ipaddress
                self.server_status[name]['ssh_port'] = ssh_port
                self.server_status[name]['rcon_port'] = rcon_port
                self.server_status[name]['ssh_status'] = 'N/A'
                self.server_status[name]['rcon_status'] = 'N/A'
                self.server_status[name]['player_status'] = 'N/A'
                self.server_status[name]['rcon_attempts'] = 0
                passwords = self.decrypt_pass(name)
                self.server_status[name]['rcon_password'] = (
                    passwords['rcon_pass'])
                self.server_status[name]['map'] = 'N/A'
                self.server_status[name]['version'] = 'N/A'
                self.add_ulc_data([GID, name])
                # Log the action
                text = 'Created a new sever called ' + str(name) + '.'
                self.output(text, 'New Server')
            elif action == 'server_edit':
                self.sql.connect()
                self.sql.c.execute(
                    'UPDATE servers SET name = ?, ipaddress = ?, GID = ?, '
                    'ssh_username = ?, ssh_password = ?, ssh_port = ?, '
                    'rcon_password = ?, rcon_port = ? WHERE ID = ?',
                    (name, ipaddress, GID, ssh_user, ssh_pass, ssh_port,
                     rcon_pass, rcon_port, serverID))
                self.sql.close(1)
                # If editing server name, del old dict value and assign new
                if self.server_edit_name != name:
                    self.server_status[name] = (
                        self.server_status[self.server_edit_name])
                    del self.server_status[self.server_edit_name]
                index = self.mes_dlg.index
                old_group_name = self.mes_group.group_name
                self.mes_dlg.Destroy()
                self.dialogs['server_edit'] = 0
                self.server_status[name]['GID'] = GID
                self.server_status[name]['ipaddress'] = ipaddress
                self.server_status[name]['ssh_port'] = ssh_port
                self.server_status[name]['rcon_port'] = rcon_port
                old_rcon_pass = self.server_status[name]['rcon_password']
                passwords = self.decrypt_pass(name)
                self.server_status[name]['rcon_password'] = (
                    passwords['rcon_pass'])
                if old_rcon_pass != self.server_status[name]['rcon_password']:
                    self.server_status[name]['player_status'] = 'N/A'
                    self.server_status[name]['rcon_attempts'] = 0
                if group_name != old_group_name:
                    for key in self.groups:
                        if self.groups[key] == old_group_name:
                            oldGID = key
                            break
                    # We're changing server group, so delete item then add
                    self.server_ulc[str(oldGID)].Freeze()
                    self.server_ulc[str(oldGID)].DeleteItem(index)
                    self.server_ulc[str(oldGID)].Thaw()
                    self.server_ulc[str(oldGID)].Update()
                    self.add_ulc_data([GID, name])
                else:
                    self.add_ulc_data([GID, name, index])
                # Log the action
                if self.server_edit_name != name:
                    text = 'Edited server now called ' + str(name) + '.'
                else:
                    text = 'Edited server called ' + str(name) + '.'
                self.output(text, 'Server Edit')

    def server_edit(self, event):
        # Get selected server
        selected = self.get_selected()
        if selected == False:
            return

        # Make sure we only open one of these dialogs
        for dlg in self.dialogs:
            if self.dialogs[dlg] == 1:
                return
        if self.dialogs['server_edit'] == 0:
            self.dialogs['server_edit'] = 1
        elif self.dialogs['server_edit'] == 1:
            return

        # Get row information
        self.sql.connect()
        results = self.sql.c.execute(
            'SELECT * FROM servers WHERE name = "' +
            str(selected['server_name']) + '"')
        for row in results:
            server_info = row
        self.sql.close()
        self.server_edit_name = server_info[1]
        passwords = self.decrypt_pass(selected['server_name'])

        # Open dialog
        self.mes_dlg = self.res.LoadDialog(None, 'mes_dlg')
        self.mes_dlg.SetWindowStyle(
            wx.DEFAULT_DIALOG_STYLE|wx.TAB_TRAVERSAL)
        # Let's us know which index to modify
        self.mes_dlg.index = selected['ulc_index']
        self.mes_id = xrc.XRCCTRL(self.mes_dlg, 'mes_id')
        self.mes_id.SetLabel(str(server_info[0]))
        self.mes_name = xrc.XRCCTRL(self.mes_dlg, 'mes_name')
        self.mes_name.SetFocus()
        self.mes_name.SetValue(str(server_info[1]))
        self.mes_ipaddress = xrc.XRCCTRL(self.mes_dlg, 'mes_ipaddress')
        self.mes_ipaddress.SetValue(str(server_info[2]))
        self.mes_group = xrc.XRCCTRL(self.mes_dlg, 'mes_group')
        self.mes_group.Clear()
        self.sql.connect()
        count = 0
        results = self.sql.c.execute('SELECT name FROM groups')
        for row in results:
            self.mes_group.Append(row[0])
            if row[0] == selected['group_name']:
                mes_group_idx = count
            else:
                count += 1
        self.sql.close()
        self.mes_group.SetSelection(mes_group_idx)
        # Lets us know if this is changed
        self.mes_group.group_name = selected['group_name']
        self.mes_ssh_user = xrc.XRCCTRL(self.mes_dlg, 'mes_ssh_user')
        self.mes_ssh_user.SetValue(str(server_info[4]))
        self.mes_ssh_pass = xrc.XRCCTRL(self.mes_dlg, 'mes_ssh_pass')
        self.mes_ssh_pass.SetValue(passwords['ssh_pass'])
        self.mes_ssh_port = xrc.XRCCTRL(self.mes_dlg, 'mes_ssh_port')
        self.mes_ssh_port.SetValue(str(server_info[6]))
        self.mes_rcon_pass = xrc.XRCCTRL(self.mes_dlg, 'mes_rcon_pass')
        self.mes_rcon_pass.SetValue(passwords['rcon_pass'])
        self.mes_rcon_port = xrc.XRCCTRL(self.mes_dlg, 'mes_rcon_port')
        self.mes_rcon_port.SetValue(str(server_info[8]))
        self.mes_name_txt = xrc.XRCCTRL(self.mes_dlg, 'mes_name_txt')
        self.mes_ipaddress_txt = xrc.XRCCTRL(self.mes_dlg, 'mes_ipaddress_txt')
        self.mes_ssh_user_txt = xrc.XRCCTRL(self.mes_dlg, 'mes_ssh_user_txt')
        self.mes_ssh_pass_txt = xrc.XRCCTRL(self.mes_dlg, 'mes_ssh_pass_txt')
        self.mes_ssh_port_txt = xrc.XRCCTRL(self.mes_dlg, 'mes_ssh_port_txt')
        self.mes_rcon_pass_txt = xrc.XRCCTRL(self.mes_dlg, 'mes_rcon_pass_txt')
        self.mes_rcon_port_txt = xrc.XRCCTRL(self.mes_dlg, 'mes_rcon_port_txt')
        self.mes_ok_btn = xrc.XRCCTRL(self.mes_dlg, 'mes_ok_btn')
        self.mes_ok_btn.dlg = 'server_edit'
        self.mes_cancel_btn = xrc.XRCCTRL(self.mes_dlg, 'mes_cancel_btn')
        self.mes_cancel_btn.dlg = 'server_edit'
        self.mes_dlg.Bind(
            wx.EVT_BUTTON, self.create_server, id=xrc.XRCID('mes_ok_btn'))
        self.mes_dlg.Bind(
            wx.EVT_BUTTON, self.dlg_closer, id=xrc.XRCID('mes_cancel_btn'))
        self.mes_dlg.Bind(wx.EVT_CLOSE, self.dlg_closer)
        self.mes_dlg.Show()

    def server_delete(self, event):
        # Get selected server
        selected = self.get_selected()
        if selected == False:
            return

        # Confirm first and then do it! NUKE IT ALL! ... j/k ... or am I?
        # Guess you'll have to review the code to find out!
        warning_dlg = wx.MessageDialog(
            self.frame,
            'Are you sure you want to delete ' +
            str(selected['server_name']) + '?', 'Warning!',
            wx.OK|wx.ICON_STOP|wx.CANCEL)
        if warning_dlg.ShowModal() == wx.ID_OK:
            warning_dlg.Destroy()
            self.sql.connect()
            self.sql.c.execute(
                'DELETE FROM servers WHERE name = "' +
                str(selected['server_name']) + '"')
            self.sql.close(1)
            # Only two areas to delete server info outside db
            del self.server_status[selected['server_name']]
            self.server_ulc[selected['GID']].Freeze()
            self.server_ulc[selected['GID']].DeleteItem(selected['ulc_index'])
            self.server_ulc[selected['GID']].Thaw()
            self.server_ulc[selected['GID']].Update()
            # Log the action
            text = 'Server ' + selected['server_name'] + ' has been deleted.'
            self.output(text, 'Server Delete')
        else:
            warning_dlg.Destroy()

    def server_key(self, event):
        # Get selected server
        selected = self.get_selected()
        if selected == False:
            return

        # Warn user about display such info publically
        warning_dlg = wx.MessageDialog(
            self.frame,
            'This will decrypt and publically display password for ' +
            selected['server_name'] + '. Are you sure you want to do this?',
            'Warning!', wx.OK|wx.ICON_STOP|wx.CANCEL)
        if warning_dlg.ShowModal() == wx.ID_OK:
            # Get hash passwords and decrypt
            passwords = self.decrypt_pass(selected['server_name'])
            # Send data to logger
            ssh_pass = (
                selected['server_name'] +
                ' SSH Pass: ' + passwords['ssh_pass'])
            rcon_pass = (
                selected['server_name'] +
                ' RCON Pass: ' + passwords['rcon_pass'])
            if self.user['ssh_access'] == '1':
                self.output(ssh_pass, 'Server Key')
            if self.user['rcon_access'] == '1':
                self.output(rcon_pass, 'Server Key')

    def daemon_action(self, event, action):
        # Get selected server
        selected = self.get_selected()
        if selected == False:
            return
        self.sql.connect()
        daemon = {}
        results = self.sql.c.execute(
            'SELECT * FROM servers WHERE name = "' +
            selected['server_name']+ '"')
        for row in results:
            daemon['name'] = row[1]
            daemon['ipaddress'] = row[2]
            daemon['ssh_username'] = row[4]
            daemon['ssh_port'] = row[6]
            if action == 'Daemon Start':
                daemon['cmd'] = self.settings['daemon_start']
                daemon['return'] = self.settings['dstart_return']
            elif action == 'Daemon Stop':
                daemon['cmd'] = self.settings['daemon_stop']
                daemon['return'] = self.settings['dstop_return']
            elif action == 'Daemon Update Start':
                daemon['cmd'] = self.settings['daemon_update_start']
                daemon['return'] = self.settings['dustart_return']
            elif action == 'Daemon Update Stop':
                daemon['cmd'] = self.settings['daemon_update_stop']
                daemon['return'] = self.settings['dustop_return']
            elif action == 'Daemon Update Check':
                daemon['cmd'] = self.settings['daemon_update_check']
                daemon['return'] = self.settings['ducheck_return']
            daemon['results'] = ''
        self.sql.close()
        passwords = self.decrypt_pass(selected['server_name'])
        daemon['ssh_password'] = passwords['ssh_pass']
        # Finally thread it
        if daemon['cmd'].find('{SESSION}') != -1:
            self.ssh_connect(wx.EVT_TOOL, daemon=daemon)
        else:
            thread.start_new_thread(self.command_daemon, (action, daemon))

    def command_daemon(self, action, daemon):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                hostname=daemon['ipaddress'],
                username=daemon['ssh_username'],
                password=daemon['ssh_password'],
                port=int(daemon['ssh_port']), timeout=5)
        except:
            text = daemon['name'] + ' - connection error'
            wx.CallAfter(self.output, text, action)
            client.close()
        else:
            text = daemon['name'] + ' - connection established'
            wx.CallAfter(self.output, text, action)
            return_output = ''

            # Do initial check first
            command = daemon['cmd'] # store for later
            if self.settings['daemon_check'] != '{NULL}':
                daemon['cmd'] = self.settings['daemon_check']
                daemon['cmd'] = self.command_parser(daemon)
                total_cmds = len(daemon['cmd'])
                count_cmds = 0
                while count_cmds < total_cmds:
                    cmd = daemon['cmd'][str(count_cmds)]
                    if type(cmd) == int:
                        # Found special pause tag, pause for # seconds
                        text = 'Pausing for ' + str(cmd) + ' seconds.'
                        wx.CallAfter(self.output, text, action)
                        sleep(cmd)
                    else:
                        wx.CallAfter(
                            self.output, daemon['name'] + '# ' + cmd, action)
                        stdin, stdout, stderr = client.exec_command(cmd)
                        for line in stdout:
                            if len(line) > 0:
                                return_output = line.strip('\n')
                                wx.CallAfter(
                                    self.output,
                                    'RAW# ' + return_output, action)
                    count_cmds += 1
                return_result = self.return_parser(
                    daemon, return_output, 'Daemon Check')
                if return_result != -1:
                    if return_result == True:
                        wx.CallAfter(self.output, 'Daemon is running.', action)
                        if (action == 'Daemon Start' or
                            action == 'Daemon Update Start'):
                            client.close()
                            wx.CallAfter(
                                self.output,
                                daemon['name'] + ' - connection closed', action)
                            wx.CallAfter(self.daemon_cleanup, daemon['name'])
                            return
                    else:
                        wx.CallAfter(
                            self.output, 'Daemon isn\'t running.', action)
                        if action == 'Daemon Stop':
                            client.close()
                            wx.CallAfter(
                                self.output,
                                daemon['name'] + ' - connection closed', action)
                            wx.CallAfter(self.daemon_cleanup, daemon['name'])
                            return

            # Now run the actual command
            daemon['cmd'] = command # restore original command
            daemon['cmd'] = self.command_parser(daemon)
            total_cmds = len(daemon['cmd'])
            count_cmds = 0
            while count_cmds < total_cmds:
                cmd = daemon['cmd'][str(count_cmds)]
                if type(cmd) == int:
                    # Found special pause tag, pause for # seconds
                    text = 'Pausing for ' + str(cmd) + ' seconds.'
                    wx.CallAfter(self.output, text, action)
                    sleep(cmd)
                else:
                    wx.CallAfter(
                        self.output, daemon['name'] + '# ' + cmd, action)
                    stdin, stdout, stderr = client.exec_command(cmd)
                    for line in stdout:
                        if len(line) > 0:
                            return_output = line.strip('\n')
                            wx.CallAfter(
                                self.output, 'RAW# ' + return_output, action)
                count_cmds += 1
            return_result = self.return_parser(daemon, return_output, action)
            if return_result == True:
                wx.CallAfter(self.output, 'Command Successful', action)
            else:
                wx.CallAfter(self.output, 'Command Failed', action)
            client.close()
            wx.CallAfter(
                self.output, daemon['name'] + ' - connection closed', action)

    def command_parser(self, daemon):
        # Using dict incase command needs to be broken up for pause tag
        new_command = {}
        count_command = 0
        new_command[str(count_command)] = daemon['cmd']
        tags = {
            '{DCHECK}': self.settings['daemon_check'],
            '{DSTART}': self.settings['daemon_start'],
            '{DSTOP}': self.settings['daemon_stop'],
            '{DUCHECK}': self.settings['daemon_update_check'],
            '{DUSTART}': self.settings['daemon_update_start'],
            '{DUSTOP}': self.settings['daemon_update_stop'],
            '{IP}': daemon['ipaddress']}
        # Replace all tags except for pause tag
        for tag in tags:
            new_command[str(count_command)] = (
                new_command[str(count_command)].replace(tag, tags[tag]))
        # Finally do the special pause tag
        while True:
            ptag = re.search('\{P\:[0-9]+\}\;?', new_command[str(count_command)])
            try:
                search = ptag.group(0)
            except AttributeError:
                break
            else:
                # Get time and convert to an integer
                temp = re.search('[0-9]+', search)
                time = int(temp.group(0))
                # Break up on the pause tag and store the two halves
                temp = new_command[str(count_command)].split(search, 1)
                new_command[str(count_command)] = temp[0]
                count_command += 1
                new_command[str(count_command)] = time
                count_command += 1
                new_command[str(count_command)] = temp[1]
        return new_command

    def return_parser(self, daemon, results, action):
        # Get condition
        condition = ''
        if action == 'Daemon Check':
            condition = self.settings['dcheck_return']
        else:
            condition = daemon['return']
        # Test condition
        if condition == '{NULL}':
            return -1
        elif condition == '{ANY}' and len(results) > 0:
            return True
        elif condition == '{NONE}' and len(results) < 1:
            return True
        elif (condition != '{ANY}' and condition != '{NONE}' and
              condition == results):
            return True
        return False

    def ssh_connect(self, event, daemon=''):
        # Get selected server
        selected = self.get_selected()
        if selected == False:
            return

        # Connect to server if not connected to one
        if self.client['ssh'] == -1:
            self.sshclient_info = {}
            self.logger_nb.SetSelection(1)
            self.ssh_cmd.SetFocus()
            self.sql.connect()
            results = self.sql.c.execute(
                'SELECT * FROM servers WHERE name = "' +
                str(selected['server_name'])+ '"')
            for row in results:
                self.sshclient_info['name'] = row[1]
                self.sshclient_info['ipaddress'] = row[2]
                self.sshclient_info['ssh_username'] = row[4]
                self.sshclient_info['ssh_port'] = row[6]
                self.sshclient_info['cmd'] = ''
                self.sshclient_info['last_cmd'] = ''
            self.sql.close()
            passwords = self.decrypt_pass(selected['server_name'])
            self.sshclient_info['ssh_password'] = passwords['ssh_pass']
            self.client['ssh'] = paramiko.SSHClient()
            self.client['ssh'].set_missing_host_key_policy(
                paramiko.AutoAddPolicy())
            try:
                self.client['ssh'].connect(
                    hostname=self.sshclient_info['ipaddress'],
                    username=self.sshclient_info['ssh_username'],
                    password=self.sshclient_info['ssh_password'],
                    port=int(self.sshclient_info['ssh_port']), timeout=5)
            except:
                text = (
                    self.sshclient_info['ssh_username'] + '@' +
                    self.sshclient_info['ipaddress'] + ' - connection error\n')
                self.ssh_output(text, 'SSH')
                self.output(text.strip(), 'SSH')
                self.client['ssh'].close()
                self.client['ssh'] = -1
                self.sshclient_info.clear()
            else:
                text = (
                    self.sshclient_info['ssh_username'] + '@' +
                    self.sshclient_info['ipaddress'] +
                    ' - connection established\n')
                self.ssh_output(text, 'SSH')
                self.output(text.strip(), 'SSH')
                self.client['chan'] = self.client['ssh'].invoke_shell()
                #self.client['ssh'].get_transport()
                thread.start_new_thread(self.ssh_thread_recv, ())
                thread.start_new_thread(self.ssh_thread_send, (daemon,))
        else:
            text = (
                'Already connected to ' + self.sshclient_info['name'] +
                '. Disconnect by typing ssh command exit.')
            self.output(text, 'SSH')

    def ssh_command(self, event):
        # Get command
        if self.client['ssh'] == -1:
            return
        self.sshclient_info['cmd'] = self.ssh_cmd.GetValue()
        self.ssh_cmd.Clear()


    def ssh_thread_recv(self):
        test = ''
        while self.client['chan'] != -1:
            if self.client['chan'].recv_ready():
                output = self.client['chan'].recv(1024)
                if not output:
                    break
                formatted = ''
                check = output.split('\n')
                for line in check:
                    sline = re.sub(
                        '\x1b(\[|\(|\))[;?0-9]*[0-9A-Za-z]', '', line)
                    #prompt = self.sshclient_info['ssh_username'] + '@'
                    #last_cmd = self.sshclient_info['last_cmd']
                    #if sline != last_cmd and sline.find(prompt) != -1:
                    #if sline.find(prompt) == -1:
                    formatted += sline
                    #length = len(sline)
                    #print 'LINE (' + str(length) + '): ' + sline
                if len(formatted) > 0:
                    wx.CallAfter(self.ssh_output, formatted)

    def ssh_thread_send(self, daemon=''):
        while self.client['chan'] != -1:
            # Proccess sending
            if len(daemon) > 0:
                # Found daemon specific action, run it first and then clear it
                cmd = daemon['cmd'].replace('{SESSION}', '')
                self.client['chan'].send(cmd + '\n')
                self.sshclient_info['last_cmd'] = self.sshclient_info['cmd']
                self.sshclient_info['cmd'] = ''
                daemon.clear()
            if len(self.sshclient_info['cmd']) > 0:
                command = self.sshclient_info['cmd']
                if command == 'exit':
                    self.ssh_disconnect(command)
                elif command != '':
                    self.client['chan'].send(self.sshclient_info['cmd'] + '\n')
                    self.sshclient_info['last_cmd'] = self.sshclient_info['cmd']
                    self.sshclient_info['cmd'] = ''
                    #formatted = (
                        #self.sshclient_info['ssh_username'] + '@' +
                        #self.sshclient_info['ipaddress'] + '# ')
                    #wx.CallAfter(self.ssh_output, formatted)

    def ssh_disconnect(self, command='exit'):
        # Properly close down the session and related data
        if self.client['ssh'] != -1:
            self.ssh_output(command + '\n')
            self.client['ssh'].close()
            self.client['chan'].close()
            self.client['ssh'] = -1
            self.client['chan'] = -1
            text = (
                self.sshclient_info['ssh_username'] + '@' +
                self.sshclient_info['ipaddress'] + ' - connection closed\n')
            self.ssh_output(text, 'SSH')
            self.output(text.strip(), 'SSH')
            self.sshclient_info.clear()

    def ssh_output(self, text, prepend=''):
        self.ssh_logger.Freeze()
        self.ssh_logger.MoveEnd()
        self.set_font(face='Courier New', rt_ctrl='ssh_logger')
        #self.ssh_logger.Newline()
        if len(prepend) > 0:
            self.ssh_logger.WriteText(
                str(self.user['name']) + ' | ' + str(prepend) + ' | ')
        self.ssh_logger.WriteText(str(text))
        self.ssh_logger.Thaw()
        # Auto scroll towards bottom and keep buffer
        range = self.ssh_logger.GetScrollRange(wx.VERTICAL)
        self.ssh_logger.Scroll(0, range)
        self.ssh_logger.SelectAll()
        range = self.ssh_logger.GetSelection()
        self.ssh_logger.SelectNone()
        if range[1] > 5000:
            diff = range[1] - 5000
            self.ssh_logger.SetSelection(0, diff)
            self.ssh_logger.Delete((0, diff))
            self.ssh_logger.SelectNone()
        self.ssh_logger.Refresh()

    def rcon_connect(self, event):
        # Get selected server
        selected = self.get_selected()
        if selected == False:
            return

        # Connect to server if not connected to one
        if self.client['rcon'] == -1:
            self.rconclient_info = {}
            self.logger_nb.SetSelection(2)
            self.rcon_cmd.SetFocus()
            self.sql.connect()
            results = self.sql.c.execute(
                'SELECT * FROM servers WHERE name = "' +
                str(selected['server_name'])+ '"')
            for row in results:
                self.rconclient_info['name'] = row[1]
                self.rconclient_info['ipaddress'] = row[2]
                self.rconclient_info['rcon_port'] = row[8]
            self.sql.close()
            passwords = self.decrypt_pass(selected['server_name'])
            self.rconclient_info['rcon_password'] = passwords['rcon_pass']
            try:
                self.client['rcon'] = (
                    SRCDS.SRCDS(self.rconclient_info['ipaddress'],
                                rconpass=self.rconclient_info['rcon_password'],
                                timeout=3))
            except:
                text = (
                    self.rconclient_info['name'] + '@' +
                    self.rconclient_info['ipaddress'] + ' - connection error')
                self.rcon_output(text, 'RCON')
                self.output(text.strip(), 'RCON')
                self.client['rcon'] = -1
                self.rconclient_info.clear()
            else:
                text = (
                    self.rconclient_info['name'] + '@' +
                    self.rconclient_info['ipaddress'] + ':' +
                    self.rconclient_info['rcon_port'] +
                    ' - connection established')
                self.rcon_output(text, 'RCON')
                self.output(text.strip(), 'RCON')

    def rcon_command(self, event):
        # Get command
        if self.client['rcon'] == -1:
            return
        command = self.rcon_cmd.GetValue()
        self.rcon_cmd.Clear()

        # If we're exiting close properly
        if command == 'exit' or command == 'disconnect':
            text = (
                self.rconclient_info['name'] + '@' +
                self.rconclient_info['ipaddress'] + ':' +
                self.rconclient_info['rcon_port'] + '# ' + command)
            self.rcon_output(str(text))
            text = (
                self.rconclient_info['name'] + '@' +
                self.rconclient_info['ipaddress'] + ':' +
                self.rconclient_info['rcon_port'] + ' - connection closed')
            self.rcon_output(text, 'RCON')
            self.output(text.strip(), 'RCON')
            self.client['rcon'].disconnect()
            self.client['rcon'] = -1
            self.rconclient_info.clear()
        else:
            response = self.client['rcon'].rcon_command(command)
            try:
                response = str(response)
            except UnicodeDecodeError:
                response = unicode(response).encode('unicode_escape')
            text = (
                self.rconclient_info['name'] + '@' +
                self.rconclient_info['ipaddress'] + ':' +
                self.rconclient_info['rcon_port'] + '# ' + command)
            self.rcon_output(str(text))
            self.rcon_output(str(response).rstrip())

    def rcon_output(self, text, prepend=''):
        self.rcon_logger.Freeze()
        self.rcon_logger.MoveEnd()
        self.set_font(face='Courier New', rt_ctrl='rcon_logger')
        if len(prepend) > 0:
            self.rcon_logger.WriteText(
                str(self.user['name']) + ' | ' + str(prepend) + ' | ')
        self.rcon_logger.WriteText(str(text))
        self.rcon_logger.Newline()
        self.rcon_logger.Thaw()
        # Auto scroll towards bottom and keep buffer
        range = self.rcon_logger.GetScrollRange(wx.VERTICAL)
        self.rcon_logger.Scroll(0, range)
        self.rcon_logger.SelectAll()
        range = self.rcon_logger.GetSelection()
        self.rcon_logger.SelectNone()
        if range[1] > 5000:
            diff = range[1] - 5000
            self.rcon_logger.SetSelection(0, diff)
            self.rcon_logger.Delete((0, diff))
            self.rcon_logger.SelectNone()
        self.rcon_logger.Refresh()

    def add_ulc_columns(self, groupID, group_name, add_to_group=True):
        # Add to group list by default
        if add_to_group==True:
            self.groups[str(groupID)] = group_name

        # Create ULC
        self.server_ulc[str(groupID)] = ulc.UltimateListCtrl(
            self.server_nb, -1,
            agwStyle=wx.LC_REPORT|wx.LC_HRULES|ulc.ULC_HAS_VARIABLE_ROW_HEIGHT|
            ulc.ULC_SINGLE_SEL)
        self.server_ulc[str(groupID)].InsertColumn(0, 'Name')
        self.server_ulc[str(groupID)].InsertColumn(1, 'IP')
        self.server_ulc[str(groupID)].InsertColumn(2, 'SSH')
        self.server_ulc[str(groupID)].InsertColumn(3, 'RCON')
        self.server_ulc[str(groupID)].InsertColumn(4, 'Players')
        self.server_ulc[str(groupID)].InsertColumn(5, 'Map')
        self.server_ulc[str(groupID)].InsertColumn(6, 'Version')
        self.server_ulc[str(groupID)].SetGradientStyle(0)
        self.server_ulc[str(groupID)].SetFirstGradientColour(
            wx.Colour(128,128,128))
        self.server_ulc[str(groupID)].SetSecondGradientColour(
            wx.Colour(255,255,255))
        self.server_ulc[str(groupID)].EnableSelectionGradient()

        # Create ULC image list
        help = wx.Bitmap(
            os.path.join(IMG, 'help.png'), wx.BITMAP_TYPE_PNG)
        warning = wx.Bitmap(
            os.path.join(IMG, 'exclamation.png'), wx.BITMAP_TYPE_PNG)
        accept = wx.Bitmap(
            os.path.join(IMG, 'accept.png'), wx.BITMAP_TYPE_PNG)
        image_list = ulc.PyImageList(16, 16)
        image_list.Add(help)
        image_list.Add(warning)
        image_list.Add(accept)
        self.server_ulc[str(groupID)].SetImageList(
            image_list, wx.IMAGE_LIST_SMALL)

        # Add to server notebook
        self.server_nb.AddPage(self.server_ulc[str(groupID)], group_name)

    def add_ulc_data(self, data):
        # Values
        groupID = data[0]
        name = data[1]
        ipaddress = self.server_status[name]['ipaddress']
        port = self.server_status[name]['rcon_port']
        ssh_status = self.server_status[name]['ssh_status']
        rcon_status = self.server_status[name]['rcon_status']
        player_status = self.server_status[name]['player_status']
        current_map = self.server_status[name]['map']
        version = self.server_status[name]['version']

        self.server_ulc[str(groupID)].Freeze()
        # Name Field
        if len(data) > 2:
            # If data has 3 elements, it means we're editing an item
            index = data[2]
            self.server_ulc[str(groupID)].SetStringItem(index, 0, name)
        else:
            index = self.server_ulc[str(groupID)].InsertStringItem(
                sys.maxint, name)
        # IP Field
        self.server_ulc[str(groupID)].SetStringItem(
            index, 1, ipaddress + ':' + port)
        # SSH Field
        if ssh_status == 'Good':
            si = 2
        elif ssh_status == 'Bad':
            si = 1
        elif ssh_status == 'N/A':
            si = 0
        self.server_ulc[str(groupID)].SetStringItem(index, 2, ssh_status, [si])
        # RCON Field
        if rcon_status == 'Good':
            ri = 2
        elif rcon_status == 'Bad':
            ri = 1
        elif rcon_status == 'N/A':
            ri = 0
        else:
            ri = 0
        self.server_ulc[str(groupID)].SetStringItem(index, 3, rcon_status, [ri])
        # Player Field
        self.server_ulc[str(groupID)].SetStringItem(index, 4, player_status)
        # Map Field
        self.server_ulc[str(groupID)].SetStringItem(index, 5, current_map)
        # Version Field
        self.server_ulc[str(groupID)].SetStringItem(index, 6, version)

        # Resize Columns
        self.server_ulc[str(groupID)].SetColumnWidth(0, wx.LIST_AUTOSIZE)
        self.server_ulc[str(groupID)].SetColumnWidth(1, wx.LIST_AUTOSIZE)
        self.server_ulc[str(groupID)].SetColumnWidth(2, wx.LIST_AUTOSIZE)
        self.server_ulc[str(groupID)].SetColumnWidth(3, wx.LIST_AUTOSIZE)
        self.server_ulc[str(groupID)].SetColumnWidth(4, wx.LIST_AUTOSIZE)
        self.server_ulc[str(groupID)].SetColumnWidth(5, wx.LIST_AUTOSIZE)
        self.server_ulc[str(groupID)].SetColumnWidth(6, wx.LIST_AUTOSIZE)
        col0 = self.server_ulc[str(groupID)].GetColumnWidth(0)
        col1 = self.server_ulc[str(groupID)].GetColumnWidth(1)
        col2 = self.server_ulc[str(groupID)].GetColumnWidth(2)
        col3 = self.server_ulc[str(groupID)].GetColumnWidth(3)
        col4 = self.server_ulc[str(groupID)].GetColumnWidth(4)
        col5 = self.server_ulc[str(groupID)].GetColumnWidth(5)
        col6 = self.server_ulc[str(groupID)].GetColumnWidth(6)
        if col0 < 50:
            self.server_ulc[str(groupID)].SetColumnWidth(0, 50)
        if col1 < 100:
            self.server_ulc[str(groupID)].SetColumnWidth(1, 100)
        if col2 < 50:
            self.server_ulc[str(groupID)].SetColumnWidth(2, 50)
        if col3 < 50:
            self.server_ulc[str(groupID)].SetColumnWidth(3, 50)
        if col4 < 75:
            self.server_ulc[str(groupID)].SetColumnWidth(4, 75)
        if col5 < 100:
            self.server_ulc[str(groupID)].SetColumnWidth(5, 100)
        if col6 < 150:
            self.server_ulc[str(groupID)].SetColumnWidth(6, 150)
        self.server_ulc[str(groupID)].Thaw()
        self.server_ulc[str(groupID)].Update()

    def decrypt_pass(self, server_name):
        passwords = {} # Unencrypted passwords stored here for return
        self.sql.connect()
        server_info = []
        results = self.sql.c.execute(
            'SELECT ssh_password, rcon_password FROM servers ' +
            'WHERE name = "' + str(server_name) + '"')
        for row in results:
            ssh_hex = row[0]
            rcon_hex = row[1]
        self.sql.close()
        cipher_key = self.user['key']
        while len(cipher_key) < 32:
            cipher_key += ' '
        cipher_obj = AES.new(cipher_key, AES.MODE_CBC, self.user['IV'])
        ciphertext = binascii.unhexlify(ssh_hex)
        ssh_pass = cipher_obj.decrypt(ciphertext)
        ssh_pass = ssh_pass.replace(' ', '')
        passwords['ssh_pass'] = str(ssh_pass)
        ciphertext = binascii.unhexlify(rcon_hex)
        rcon_pass = cipher_obj.decrypt(ciphertext)
        rcon_pass = rcon_pass.replace(' ', '')
        passwords['rcon_pass'] = str(rcon_pass)
        return passwords

    def output(self, text, prepend=''):
        if self.logger_nb.GetSelection() != 0:
            self.logger_nb.SetPageImage(0, 1)
        self.logger.Freeze()
        self.logger.MoveEnd()
        self.set_font(face='Courier New')
        if len(prepend) > 0:
            prepend = str(self.user['name']) + ' | ' + str(prepend) + ' | '
            self.logger.WriteText(prepend)
        self.logger.WriteText(str(text))
        if self.settings['enable_debuglog'] == 1:
            self.logging.debug(prepend + text)
        self.logger.Newline()
        self.logger.Thaw()
        # Auto scroll towards bottom and keep buffer
        range = self.logger.GetScrollRange(wx.VERTICAL)
        self.logger.Scroll(0, range)
        self.logger.SelectAll()
        range = self.logger.GetSelection()
        self.logger.SelectNone()
        if range[1] > 5000:
            diff = range[1] - 5000
            self.logger.SetSelection(0, diff)
            self.logger.Delete((0, diff))
            self.logger.SelectNone()
        self.logger.Refresh()

    def set_font(
        self, attr=None, color=wx.BLACK, size=10,
        face="Trebuchet MS", weight=wx.FONTSTYLE_NORMAL, underline=False,
        rt_ctrl='logger'):
        if attr == None:
            self.text_attr.SetTextColour(color)
            self.text_attr.SetFontFaceName(face)
            self.text_attr.SetFontSize(size)
            self.text_attr.SetFontWeight(weight)
            self.text_attr.SetFontStyle(wx.FONTSTYLE_NORMAL)
            self.text_attr.SetFontUnderlined(underline)
            if rt_ctrl == 'logger':
                self.logger.SetDefaultStyle(self.text_attr)
            elif rt_ctrl == 'ssh_logger':
                self.ssh_logger.SetDefaultStyle(self.text_attr)
            elif rt_ctrl == 'rcon_logger':
                self.rcon_logger.SetDefaultStyle(self.text_attr)
        else:
            font = wx.Font(size, wx.SWISS, wx.NORMAL, wx.NORMAL)
            font.SetFaceName(face)
            font.SetPointSize(size)
            font.SetWeight(weight)
            font.SetStyle(wx.FONTSTYLE_NORMAL)
            font.SetUnderlined(underline)
            attr.SetFont(font)
            return attr

    def get_selected(self):
        # Get selected server
        group_name = self.server_nb.GetPageText(self.server_nb.GetSelection())
        for key in self.groups:
            if self.groups[key] == group_name:
                groupID = key
                break
        index = self.server_ulc[str(groupID)].GetFocusedItem()
        if index == -1:
            # Cancel function if we failed to find index
            return False
        server_name = self.server_ulc[str(groupID)].GetItemText(index)
        selected = self.server_ulc[str(groupID)].IsSelected(index)
        if selected == False:
            # Cancel function if it's not truly selected
            return False
        selected = {'group_name': group_name,
                    'GID': str(groupID),
                    'server_name': server_name,
                    'ulc_index': index}
        return selected

    def dlg_closer(self, event):
        for dlg in self.dialogs:
            if self.dialogs[dlg] == 1:
                if dlg == 'sign_in':
                    self.msi_dlg.Destroy()
                    self.dialogs[dlg] = 0
                elif dlg == 'new_user':
                    self.mnu_dlg.Destroy()
                    self.dialogs[dlg] = 0
                elif dlg == 'new_server':
                    self.mns_dlg.Destroy()
                    self.dialogs[dlg] = 0
                elif dlg == 'server_edit':
                    self.mes_dlg.Destroy()
                    self.dialogs[dlg] = 0
                elif dlg == 'settings':
                    self.msd_dlg.Destroy()
                    self.dialogs[dlg] = 0

    def OnPageChanged(self, event):
        #text = ('Page Changed: ' + str(event.GetSelection()) + ' ' +
                #self.server_nb.GetPageText(event.GetSelection()))
        #page_name = self.server_nb.GetPageText(0)
        #self.output(page_name)
        #if self.client['rcon'] != -1:
            #info, players = self.client['rcon'].status()
            #self.output(str(info['current_playercount']))
            #self.output(str(info['max_players']))
            #self.output(str(players))
        if self.logger_nb.GetSelection() == 0:
            self.logger_nb.SetPageImage(0, 0)

if __name__ == '__main__':
    app = Mantib(False)
    app.MainLoop()