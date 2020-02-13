#!/usr/bin/python

import sys
import socket
import threading
import select

lock = threading.Lock()
max_msg = 1024

reg_req = '<REGISTER, '
login_req = '<LOGIN, '
msg_req = '<MSG, '
disc_req = '<DISCONNECT>'
clist_req = '<CLIST>'

errors = ['0x00 Success', '0x01 Access Denied', '0x02 Duplicate Client ID',
          '0x03 Invalid File_ID', '0x04 Invalid IP addressand/or port',
          '0xFF Invalid Format']

userdb = []
chat = []
online = {}

def add_user(user, passw):
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
            
def logon(user, passw):
    ck_logon = (user, passw)
    lock.acquire()
    if ck_logon not in userdb and user not in online.values():
        lock.release()
        return errors[0]
    else:
        lock.release()
        return errors[1]

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

def handle_req(sock):
    read_set = [sock]
    empty = []
    select.select(read_set, empty, empty)
    msg = sock.recv(max_msg)
    print(msg)
    if reg_req in msg:
        indexer = len(reg_req)
        login = msg[indexer:]
        user = login[:login.find(',')]
        passw = login[len(user)+1:-1]
        ck = check_userdb(user, passw)
        if ck == errors[0]:
            online[sock] = user
            add_user(user, passw)
            enter_chat(sock, user)
        else:
            sock.send(ck)
            handle_req(sock)

    elif login_req in msg:
        indexer = len(login_req)
        login = msg[indexer:]
        user = login[:login.find(',')]
        passw = login[(len(user)+1):-1]
                      
        ck = logon(user, passw)
        if ck == errors[0]:
            online[sock] = user
            enter_chat(sock, user)
        else:
            sock.send(ck)
            sock.close()                     
    elif msg == disc_req:
        sock.send(disc_req)
        sock.close()                     
    else:
        sock.send(errors[5])
        handle_req(sock)

def main():
    if len(sys.argv) > 1:
        try:
            with open(sys.argv[1], 'r') as f:
                f.seek(0)
                for line in f.read():
                      usr = line[:line.find(',')]
                      ps = line[len(usr)+1:]
                      userdb.append((usr, ps))
        except IOError:
                print("Unable to locate file: " + sys.argv[1])
                print("USAGE: pyserve [optional filename]")
    else:
        try:
            f = open('nothing_to_see_here', 'a+')
            f.seek(0)
            for line in f.read():
                usr = line[:line.index(',')]
                print(usr)
                ps = line[len(usr) +1:]
                print(ps)
                userdb.append((usr, ps))
            f.close
        except:
            print('UNABLE TO READ FILE')

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_address = ('127.0.0.1', socket.htons(6000))
    server.bind(server_address)
    server.listen(5)

    active_threads = []
    while True:
        client, client_address = server.accept()
        client.setblocking(0)
        t = threading.Thread(target=handle_req, args=(client, ))
        active_threads.append(t)
        t.start()

main()
