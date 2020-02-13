#!/usr/bin/python
import sys
import socket
import select

max_msg = 4096

errors = ['0x00 Success', '0x01 Access Denied', '0x02 Duplicate Client ID',
          '0x03 Invalid File_ID', '0x04 Invalid IP addressand/or port',
          '0xFF Invalid Format']

def begin_comm(sock):
    while True:
        read_set = [sock,sys.stdin,]
        empty = []
        rr, wr, err = select.select(read_set, empty, empty, 60.0)
        if sock in rr:
            msg = sock.recv(max_msg)
            print(msg)
            if msg in errors:
                if msg == errors[1]:
                    sock.send("<DISCONNECT>")
                    sock.close()
                    return
                if msg == errors[2]:
                    user = raw_input('USERNAME: ')
                    passw = raw_input('PASSWORD: ')
                    sock.send('<REGISTER, ' + user + ',' + passw + '>')
        elif sys.stdin in rr:
            s = raw_input()
            if s == 'DISCONNECT':
                sock.send('<DISCONNECT>')
                sock.close()
                return
            elif s == 'CLIST':
                sock.send('<CLIST>')
            else:
                sock.send('<MSG, ' + s + '>')

def main():
    print("#####\nSELECT OPTION FROM THE MENU BELOW:\n" +
          "#####\n1. REGSITER\n2. LOGIN\n3. DISCONNECT\n")
    selection = raw_input('Selection: ')
    if selection == '1' or selection == '2':
        user = raw_input('Username: ')
        passw = raw_input('Password: ')
    else:
        exit(0)       
    port = socket.htons(6000)
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(('127.0.0.1', port))
    if selection == '1':
        client.send('<REGISTER, ' + user + ',' + passw + '>')
        print("Connecting to server...")
        begin_comm(client)
    elif selection == '2':
        client.send('<LOGIN, ' + user + ',' + passw + '>')
        print("Connecting to server...")
        begin_comm(client)
    else:
        print("Invalid selection")
        exit(0)
        
main()
