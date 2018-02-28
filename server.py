#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2018 transpalette <transpalette@arch-cactus>
#
# Distributed under terms of the MIT license.

"""
IRC Server class: handles the connection, the configuration...
"""

import socket
import select
import json

from pathlib import Path

class IRCServer:
    
    config_location = str(Path.home()) + "/.config/IRCNotificationBot/config.json"

    def __init__(self, callback):
        with open(config_location) as config_file:
            config = json.load(config_file)

        self._channel = config['channel']
        self._botName = config['botName']
        self._admin = config['admin']
        self._exitCode = config['exitCode']
        self._timeout = config['timeout']
        self._notifs = config['notifications']

        self._running = False
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.connect((config['server'], config['port']))
        self._sock.setblocking(0)

        self._callback = callback

        self.join_channel()


    def join_channel(self):
        # Authenticating
        self._sock.send(bytes("USER "+ self._botName +" "+ self._botName +" "+ self._botName + " " + self._botName + "\n", "UTF-8")) #We are basically filling out a form with this line and saying to set all the fields to the bot nickname.
        self._sock.send(bytes("NICK " + self._botName + "\n", "UTF-8")) # Assign the nickname to the bot

        self._sock.send(bytes("JOIN " + self._channel + "\n", "UTF-8"))
        ircmsg = ""

        while ircmsg.find("End of /NAMES list.") == -1:
            if select.select([self._sock], [], [], self._timeout)[0]:
                ircmsg = self._sock.recv(2048).decode("UTF-8").strip('\n\r')

        Util.notify('IRC Notifier', 'Successfuly joinned {}'.format(self._channel))


    # Respond to pings
    def pong(self):
        self._sock.send(bytes("PONG :pingis\n", "UTF-8"))


    # Receive a command / message
    def recv(self):
        while self._running:
            ready = select.select([self._sock], [], [], self._timeout)

            if ready[0]:
                ircmsg = self._sock.recv(1024).decode("UTF-8").strip('\n\r')
            
                '''
                Format of a private message from IRC:
                    [Nick]!~[hostname]@[IP Address] PRIVMSG [channel] :[message]
                '''
                if ircmsg.find("PRIVMSG") != -1:
                    sender = ircmsg.split('!', 1)[0][1:]
                    message = ircmsg.split('PRIVMSG', 1)[1].split(':', 1)[1]
                    self._callback.process_message(message, sender)
                elif ircmsg.find("PING") != -1:
                    self.pong()
                elif ircmsg.find("JOIN") != -1:
                    self._callback.user_joinned(ircmsg.split('!')[0][1:])
                elif ircmsg.find("PART") != -1:
                    self._callback.user_left(ircmsg.split('!')[0][1:])

    
    def watch(self):
        self._running = True
        self._recv()


    def stop(self):
        self._running = False
        self._sock.send(bytes("QUIT \n", "UTF-8"))
        self._sock.close()
