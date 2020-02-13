#!/usr/bin/python

###################################### pyfileserve.py #######################################
# Author: John La Velle
# UMN ID: lavel026
# Class: CSCI 4211
# Instructor: Prof. David Du
# Created: Spring 2017
# © John La Velle 2017
#############################################################################################

########################################## MODULES ##########################################

import socket
import threading
import select
import sys
import random

##################################### GLOBAL VARIABLES #####################################

lock = threading.Lock()
max_msg = 1024

chat_select = '<CHATROOM>'
reg_req = '<REGISTER, '
login_req = '<LOGIN, '
msg_req = '<MSG, '
disc_req = '<DISCONNECT>'
clist_req = '<CLIST>'

file_select = '<TRANSFER>'
flist_req = '<FLIST>'
fput_req = '<FPUT, '
fget_req = '<FGET, '

flist = {}
cflist = {}

userdb = []
chat = []
online = {}

errors = ['0x00 Success', '0x01 Access Denied', '0x02 Duplicate Client ID',
          '0x03 Invalid File_ID', '0x04 Invalid IP addressand/or port',
          '0xFF Invalid Format']

################################# FILE TRANSFER FUNCTIONS #################################

def get_id(a, b):
    a = a + 1
    b = b * 3
    a = random.randint(a, b)
    return a, b

#--------------------------------------------------------------------------------------#

def handle_file_functions(sock):
    id_, roof = 0, 10
    rset = [sock]
    empty = []
    while True:
        r, w, err = select.select(rset, empty, empty)
        msg = sock.recv(max_msg)
        # File Transfer Handling #
        if flist_req in msg:
            if len(flist) == 0:
                sock.send("No files uploaded")
            else:
                sendr = "FILE LIST: \n"
                for k in flist:
                    sendr += flist[k] + ': ' + str(k) + '\n'
                sendr = sendr[:-1]
                sock.send(sendr)
        elif fput_req in msg:
            id_, roof = get_id(id_, roof)
            creds = msg[len(fput_req):-1]
            print(creds)
            name, caddr, cport = [x for x in creds.split(',')]
            flist[id_] = name
            cflist[id_] = (caddr, cport)
            sock.send(errors[0])
        elif fget_req in msg:
            fid = msg[len(fget_req):-1]
            f_id = int(fid)
            if f_id in cflist.keys():
                addr = cflist[f_id][0]
                portr = cflist[f_id][1]
                sock.send(addr + ' : ' + portr)
            else:
                sock.send(errors[3])

################################### CHATROOM FUNCTIONS ####################################

def enter_chat(sock, user):
    read_set = [sock]
    empty = []
    lock.acquire()
    chat_log = '\n'.join(chat)
    sock.send(chat_log)
    lock.release()
    while True:
        r, w, err = select.select(read_set, empty, empty)
        if sock in r:
            msg = sock.recv(max_msg)
            if msg_req in msg:
                new_msg = msg[len(msg_req):-1]
                if len(new_msg) == 0 or new_msg == "\n":
                    continue
                print(new_msg)
                lock.acquire()
                chat.append(user + ': ' + new_msg)
                chat_log = '\n'.join(chat)
                for s in online.keys():
                    s.send(chat_log)
                lock.release()
            if msg == disc_req:
                print(msg + '  from ' + user)
                del online[sock]
                sock.send(disc_req)
                sock.close()
                exit(0)
            if msg == clist_req:
                sock.send('\n'.join(online.values()))
        else:
            print(err)

################################ CONTROLLER FUNCTIONS ####################################

def add_user(user, passw):
    lock.acquire()
    if len(sys.argv) > 1:
        try:
            f = open(sys.argv[1], 'a+')
            f.write(user +',' + passw + '\n')
            f.close()
        except:
            fx = open('nothing_to_see_here', 'a+')
            fx.write(user + ',' + passw + '\n')
            f.close()
    else:
        f = open('nothing_to_see_here', 'a+')
        f.write(user + ',' + passw + '\n')
        f.close()
    lock.release()

#--------------------------------------------------------------------------------------#

def decipher(sock, user):
    read_set = [sock]
    while True:
        r, w, err = select.select(read_set, empty, empty)
        msg = sock.recv(1024)
        if msg == chat_select:
            enter_chat(sock, user)
        elif msg == file_select:
            handle_file_functions(sock)
        elif msg == disc_req:
            sock.send(disc_req)
            return disc_req

#--------------------------------------------------------------------------------------#

def logon(user, passw):
    ck_logon = (user, passw)
    lock.acquire()
    if ck_logon not in userdb and user not in online.values():
        lock.release()
        return errors[0]
    else:
        lock.release()
        return errors[1]

#--------------------------------------------------------------------------------------#

def check_userdb(user, passw):
    ck_logon = (user, passw)
    lock.acquire()
    if ck_logon in userdb:
        lock.release()
        return errors[2]
    else:
        for u in userdb:
            if user == u[0]:
                lock.release()
                return errors[2]
        userdb.append(ck_logon)
        lock.release()
        return errors[0]

#--------------------------------------------------------------------------------------#

def handle_login_req(sock):
    rset = [sock]
    empty = []
    while True:
        r, w, err = select.select(rset, empty, empty)
        msg = sock.recv(max_msg)
        # Login/Register Request Handling #
        if reg_req in msg:
            indexer = len(reg_req)
            login = msg[indexer:]
            user = login[:login.find(',')]
            passw = login[len(user)+1:-1]
            ck = check_userdb(user, passw)
            if ck == errors[0]:
                online[sock] = user
                add_user(user, passw)
                msg = decipher(sock, user)
                if msg == disc_req:
                    sock.close()
                    return
            else:
                sock.send(ck)
        elif login_req in msg:
            indexer = len(login_req)
            login = msg[indexer:]
            user = login[:login.find(',')]
            passw = login[(len(user)+1):-1]                         
            ck = logon(user, passw)
            if ck == errors[0]:
                online[sock] = user
                msg = decipher(sock, user)
                if msg == disc_req:
                    sock.close()
                    return
            else:
                sock.send(ck)
                sock.close()
        elif msg == disc_req:    # Disconnect Handling
            sock.send(disc_req)
            sock.close()
            return
        else:                   # Invalid Formatting Issue
            sock.send(errors[5])
            handle_req(sock)

########################################## MAIN ##########################################

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_address = ('127.0.0.1', socket.htons(6000))
    server.bind(server_address)
    server.listen(5)

    active_threads = []
    while True:
        client, client_address = server.accept()
        client.setblocking(0)
        t = threading.Thread(target=handle_login_req, args=(client, ))
        active_threads.append(t)
        t.start()
        # Handle returned threads here #
        
########################################## MAIN ##########################################

main()

###################################### pyfileserve.py ####################################
