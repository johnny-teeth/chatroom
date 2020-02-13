#!/usr/bin/python

###################################### pyfileclient.py ######################################
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
import os

##################################### GLOBAL VARIABLES #####################################

f_req = '<FGET, '
fpath = os.getcwd() + '/files/'
lock = threading.Lock()

errors = ['0x00 Success', '0x01 Access Denied', '0x02 Duplicate Client ID',
          '0x03 Invalid File_ID', '0x04 Invalid IP addressand/or port',
          '0xFF Invalid Format']


################################# FILE TRANSFER FUNCTIONS #################################

# Handles file requests from peers
def peer_req(sock):
    select.select([sock], [], [])
    msg = sock.recv(1024)
    if f_req in msg:
        fname = msg[len(f_req):-1]                # Parse file name from msg
        lock.acquire()
        try:
            sz = os.stat(fpath + fname).st_size   # Get file size
            lock.release()
        except:
            sock.send("ERROR FILE NOT AVAILABLE")
            sock.close()
            lock.release()
            return
        sock.send(str(sz))                        # Send file size for proper recv
        select.select([sock], [], [])
        ck = sock.recv(4096)                      # Confirmation from Peer
        if sz == ck:
            lock.acquire()
            f = open(fpath + fname, 'r')
            send_fl = f.read()
            sock.send(send_fl)                    # Send entire read contents to Peer
            f.close()
            lock.release()
            select.select([sock], [], [])
            msg = sock.recv(4096)
            if msg == '<DISCONNECT>':             # Close Peer connection
                sock.shutdown()
                sock.close()
            else:
                sock.close()
    else:
        sock.close()

#--------------------------------------------------------------------------------------#

# Creates P2P Socket connections for Peers
def peer_connect(my_port):
    peers = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    peers.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    peers_address = ('127.0.0.1', socket.htons(my_port))
    peers.bind(peers_address)
    peers.listen(5)
    while True:
        other_peer, others_addr = peers.accept()
        other_peer.setnonblocking(0)
        op_t = threading.Thread(target=peer_req, args=(other_peer, ))
        op_t.start()

#--------------------------------------------------------------------------------------#

# Receives files from other clients
def receive_file(port, addr, fname):
    peer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    peer.connect((addr, socket.htons(port)))
    peer.send('<FGET, ' + fname)                    # Send file name to client w/ expected format
    select.select([peer], empty, empty)
    size = peer.recv(1024)                          # Receive file size from client
    peer.send(size)                                 # Acknowledge file size
    select.select([peer], empty, empty)
    whole_file = peer.recv(int(size)+1)             # Receive entire file
    lock.acquire()
    new_f = open(fpath + fname, 'a+')               # Open file and write contents
    num_writes = new_f.write(whole_file)
    f.close()
    lock.release()
    peer.send('<DISCONNECT>')                       # Disconnect from peer
    peer.close()
    if num_writes != int(size):                     # Compare file size to amount written
        print("Wrote " + str(num_writes) +
              " when file size was " + size)
    else:                                           # Print as conditioned
        print("File Received: " + fname)

#--------------------------------------------------------------------------------------#

# Main File Transfer Interface
def handle_file_req(my_port, client):
    while True:                                     # Offer user options
        print("#####\nSELECT OPTION FROM THE MENU BELOW:\n" +
              "1. Get File List\n2. Upload File\n3. Retrieve File\n" +
              "4. Go to main menu\n"+
              "#####\n")
        selection = raw_input('Selection: ')
        # Traverse Selection values
        if selection == '1':                        # Get File List
            msg = "<FLIST>"
        elif selection == '2':                      # Inform server of file
            f_name = raw_input('Filename: ')
            msg = '<FPUT, ' + f_name + ',127.0.0.1,' + my_port + '>'
        elif selection == '3':                      # File Transfer
            fid = raw_input('File ID: ')
            msg = '<FLIST>'
            client.send(msg)                        # Get File List
            select.select(rset, empty, empty)
            temp = client.recv(4096)                # Parse File Name from File List
            temp_srch = [z for z in temp.split('\n') if (' ' + fid) in z] 
            fname, fid = [y.strip() for y in temp.split(':')]
            msg = '<FGET, ' + fid + '>'             # Get Peer information for transfer
            select.select(rset, empty, empty)
            c_creds = client.recv(4096)             # Parse Peer information
            addr, port = [x.strip() for x in c_creds.split(':')]
            receive_file(addr, int(port), fname)    # Perform file transfer
            msg = '<FPUT, ' + fname + ',127.0.0.1,' +  my_port + '>' # Create FPUT message
        else:
            return
        # Send msg to server and await response
        client.send(msg)
        rset = [client, ]
        empty = []
        select.select(rset, empty, empty)
        ret = client.recv(4096)
        print(ret)                                  # Print server response


#################################### CHATROOM FUNCTIONS #####################################

# Constant loop selecting 'fd's until DISCONNECT
def handle_chat_req(sock):
    while True:
        read_set = [sock,sys.stdin,]
        empty = []
        rr, wr, err = select.select(read_set, empty, empty, 60.0)
        if sock in rr:
            msg = sock.recv(max_msg)
            print(msg)              # Should always refresh Chat
        elif sys.stdin in rr:
            s = raw_input()
            if s == 'QUIT':
                return
            elif s == 'CLIST':
                sock.send('<CLIST>')
            else:
                sock.send('<MSG, ' + s + '>')

################################# MAIN CONTROLLER FUNCTIONS #################################
                 
def handle_login(my_port):
    print("####### WELCOME TO CHATROOM & P2P ########" +
          "\n-- SELECT OPTION FROM THE MENU BELOW --\n" +
          "\n1. REGSITER\n2. LOGIN\n3. QUIT\n")
    attempts = 3                 
    selection = raw_input('Selection: ')
    if selection == '1' or selection == '2':
        user = raw_input('Username: ')
        passw = raw_input('Password: ')
    else:
        exit(0)
    # Connect to server occurs here                
    port = socket.htons(6000)
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(('127.0.0.1', port))
    # Traverse selection values                
    if selection == '1':
        client.send('<REGISTER, ' + user + ',' + passw + '>')
        print("Connecting to server...")
        select.select([client, ], [], [])
        msg = client.recv(1024)
        if msg == errors[0]:
            server_connect(my_port, client)
        else:   # If unsuccessful, allow 3 attempts
            while attempts > 0 and msg != errors[0]:     
                print(msg)
                user = raw_input('USERNAME: ')
                passw = raw_input('PASSWORD: ')
                sock.send('<REGISTER, ' + user + ',' + passw + '>')
                select.select([client, ], [], [])
                msg = client.recv(1024)
                attempts -= 1
            if msg == errors[0]:
                server_connect(my_port, client)
            else:    # After 3 attempts, disconnect
                client.send('<DISCONNECT>')
                client.close()
                return
    elif selection == '2':
        client.send('<LOGIN, ' + user + ',' + passw + '>')
        print("Connecting to server...")
        select.select([client, ], [], [])
        msg = client.recv(1024)
        if msg == errors[0]:    # Success
            server_connect(my_port, client)
        if msg == errors[1]:    #Access Denied
            sock.send("<DISCONNECT>")
            sock.close()
            return
        else:                   # Should never receive anything other
            print(msg)          # Than errors[0] & errors[1]
            sock.send('<DISCONNECT>')
            sock.close()
            return
    else:
        print("Invalid selection: Terminating Connection\n")
        sock.send('<DISCONNECT>')
        sock.close()
        return

#--------------------------------------------------------------------------------------#

# Connects to P2P main Server                 
def server_connect(my_port, client):
    while True:
        print("-- Select from the following options --\n" +
              "1. Chatroom\n2. File Transfer\n3. Disconnect\n" +
              "----------------\n")
        selection = raw_input('--Selection: ')
        if selection == '1':
            print("--- TYPE QUIT WHEN FINISHED WHEN EXITING ---")
            client.send("<CHATROOM>")
            handle_chat_req(client)
        elif selection == '2':
            client.send("<TRANSFER>")
            handle_file_req(my_port, client)
        elif selection == '3':
            client.send('<DISCONNECT>')
            client.close()
            return

########################################## MAIN ##########################################

# Creates thread for user and thread for file transfer
# NOTE: Do not run multiple clients from the same directory
def main():
    if len(sys.argv) > 1:
        my_port = int(sys.argv[1])
        if my_port < 4999 and my_port > 5999:
            print("USAGE: python pyclient.py [port: (5000-5999)]")
            exit(-1)
    else:
        print("USAGE: python pyclient.py [port: (5000-5999)]")
        exit(-1)
    if not os.path.isdir(fpath):                # If there is not a files dir
        os.mkdirs(fpath)                        # It is created
    peer_t = threading.Thread(target=peer_connect, args=(my_port, ))
    server_t = threading.Thread(target=handle_login, args=(my_port, ))
    server_t.start()
    peer_t.start()
    server_t.join()

########################################## MAIN ############################################

main()

###################################### pyfileclient.py #####################################
