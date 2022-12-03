"""
    Python 3
    Usage: python3 TCPClient3.py localhost 12000
    coding: utf-8
    
    Author: Wei Song (Tutor for COMP3331/9331)
"""
from socket import *
import sys
import os
import json
from _thread import *
from datetime import *
from threading import Timer
import random

def login(username, password, clientSocket, host, port):
    message = 'login' + " " + username + " " + password + " " + str(host) + " " + str(port)
    clientSocket.sendall(message.encode())
    while True:
        data = clientSocket.recv(1024)
        receivedMessage = data.decode()
        if receivedMessage == 'login_successful':
            print('Welcome!')
            return username
        elif receivedMessage == 'login_failed':
            print('Invalid Password. Please try again')
            username = input("Username: ")
            password = input("Password: ")
            message = 'login' + " " + username + " " + password + " " + str(host) + " " + str(port)
            clientSocket.sendall(message.encode())
        elif receivedMessage == 'login_fail_blocked':
            print('Invalid Password. Your account has been blocked. Please try again later')
            exit()
        elif receivedMessage == 'blocked':
            print('Your account is blocked due to multiple authentication failures. Please try again later')
            exit()

# AED case, list all other active edge devices
def list_aeds(username):
    message = "list_AEDs" + " " + username
    clientSocket.sendall(message.encode())
    while True:
        data = clientSocket.recv(1024)
        receivedMessage = data.decode()
        if receivedMessage == '':
            continue
        elif receivedMessage == 'NED':
            print('no other active edge devices')
            break
        else:
            messages = receivedMessage.split(' ,,, ')
            for split_message in messages:
                print(split_message)
            break

# EDG case, generate file in client
def edg(username, fileID, dataAmount):
    print('The edge device is generating ' + split_command[2] + ' data samples...')
    fileName = username + '-' + fileID + '.txt'
    f = open(fileName, 'w')
    # random integer between 0 and 9
    for i in range(int(dataAmount) - 1):
        f.write(str(random.randint(0,9)) + '\n')
    f.write(str(random.randint(0,9)))
    f.close()
    print('Data generation done, ' + split_command[2] + ' data samples have been generated and stored in the file ' + username + '-' + split_command[1] + '.txt')
    
# DTE case, delete file in server
def delete_file(username, fileID):
    message = "delete_file" + " " + username + " " + fileID
    clientSocket.sendall(message.encode())
    while True:
        data = clientSocket.recv(1024)
        receivedMessage = data.decode()
        if receivedMessage == 'deleted':
            print('file with ID of ' + fileID + ' has been successfully removed from the central server')
            break
        elif receivedMessage == 'not deleted':
            print('the file does not exist at the server side')
            break
            
# SCS case, perform computation in server
def server_compute(username, fileID, computationOperation):
    message = "server_compute" + " " + username + " " + fileID + " " + computationOperation
    clientSocket.sendall(message.encode())
    while True:
        data = clientSocket.recv(1024)
        receivedMessage = data.decode()
        if receivedMessage == '':
            continue
        else:
            print(receivedMessage)
            break

# UED case, upload edge data to server
def upload_edge_data(username, fileID):
    fileName = username + '-' + fileID + '.txt'
    fileData = ''
    dataAmount = 0
    if os.path.exists(fileName):
        with open(fileName, 'r') as filedata:
            for textline in filedata.readlines():
                fileData = fileData + textline
                dataAmount += 1
        filedata.close()
        message = "download_file" + " " + username + " " + fileID + " " + str(dataAmount) + " " + fileData
        clientSocket.sendall(message.encode())
        while True:
            data = clientSocket.recv(1024)
            receivedMessage = data.decode()
            if receivedMessage == 'server received file':
                print('Data file with ID of ' + fileID + ' has been uploaded to server')
                break
        
    else:
        print('Data file with ID of ' + fileID + ' does not exist in the client side.')
        return   
    
# UVF case, upload file to audience username
def uvf(presenter_username, fileName, audience_username):
    # first, get available edge devices of presenter username and store in aed_list
    message = "list_AEDs" + " " + presenter_username
    clientSocket.sendall(message.encode())
    aed_list = []
    audience_ip = ''
    audience_port = ''
    audience_active = False
    while True:
        data = clientSocket.recv(1024)
        receivedMessage = data.decode()
        if receivedMessage == '':
            continue
        elif receivedMessage == 'NED':
            print(audience_username + ' is offline, cannot upload file to it')
            return
        else:
            messages = receivedMessage.split(' ,,, ')
            for split_message in messages:
                aed_info = split_message.split('; ')
                if (aed_info[0] == audience_username):
                    audience_ip = aed_info[1]
                    audience_port = aed_info[2]
                    audience_active = True
                    break
            break
    # username not found, print error message and return
    if not audience_active:
        print(audience_username + ' is offline, cannot upload file to it')
        return
    
    if os.path.exists(fileName):
        # read as binary
        udpSocket = socket(AF_INET, SOCK_DGRAM)
        fileSize = os.path.getsize(fileName)
        message = 'SENDING_FILE' + '; ' + presenter_username + '; ' + fileName + '; ' + str(fileSize)
        udpSocket.sendto(message.encode(), (audience_ip, int(audience_port)))
        
        with open(fileName, 'rb') as file:
            fileContent = file.read(1024)
            udpSocket.sendto(fileContent, (audience_ip, int(audience_port)))
            while fileContent:
                fileContent = file.read(1024)
                udpSocket.sendto(fileContent, (audience_ip, int(audience_port)))
        file.close()
        udpSocket.close()
        print('Data file with name of ' + fileName + ' has been transmitted to ' + audience_username)
    else:
        print('Data file with name of ' + fileName + ' does not exist at presenter side')
        return
        
def receive_vid_file(serverSocket):
    while True:
        data, clientAddress = serverSocket.recvfrom(1024)
        receivedMessage = data.decode()
        splitMessage = receivedMessage.split('; ')
        origFileSize = int(splitMessage[3])
        if (splitMessage[0] == 'SENDING_FILE'):
            fileName = splitMessage[1] + '_' + splitMessage[2]
            binary_file = open(fileName, "wb")
            print('Initiated file transfer')
            while True:
                fileSize = os.path.getsize(fileName)
                if fileSize == origFileSize:
                    print('Data file with the name of ' + splitMessage[2] + ' has been received from ' + splitMessage[1])
                    break
                else:
                    binary_data, clientAddress = serverSocket.recvfrom(1024)
                    binary_file.write(binary_data)
            binary_file.close()
        

# Server would be running on the same host as Client
if len(sys.argv) != 4: 
    print("\n===== Error usage, python3 TCPClient3.py SERVER_IP SERVER_PORT UDP_PORT_NUM ======\n")
    exit(0)
serverHost = sys.argv[1]
serverPort = int(sys.argv[2])
serverAddress = (serverHost, serverPort)

# define a socket for the client side, it would be used to communicate with the server
clientSocket = socket(AF_INET, SOCK_STREAM)

# build connection with the server and send message to it
clientSocket.connect(serverAddress)

# udp server
udpPort = int(sys.argv[3])
serverSocket = socket(AF_INET, SOCK_DGRAM)
serverSocket.bind((serverHost, udpPort))
start_new_thread(receive_vid_file, (serverSocket, ))

# authentication
username = input("Username: ")
password = input("Password: ")
username = login(username, password, clientSocket, serverHost, udpPort)

while True:
    command = input("Enter one of the following commands  (EDG, UED, SCS, DTE, AED, UVF, OUT):\n")
    # OUT case, logout
    split_command = command.split(' ')
    if command == "OUT":
        message = "logout" + " " + username
        clientSocket.sendall(message.encode())
        print('Bye, ' + username + '!')
        clientSocket.close()
        exit()
    elif command == "AED":
        list_aeds(username)
        continue
    elif split_command[0] == "EDG":
        if len(split_command) == 3:
            if split_command[1].isdigit() and split_command[2].isdigit():
                edg(username, split_command[1], split_command[2])
            else:
                print('the fileID or dataAmount are not integers, you neeed to specify the parameter as integers')
        else:
            print('EDG command requires fileID and dataAmount as arguments.')
        continue
    elif split_command[0] == "DTE":
        if len(split_command) == 2:
            if split_command[1].isdigit():
                delete_file(username, split_command[1])
            else:
                print('the fileID is not an integer, you need to specify the parameter as integer')
        else:
            print('DTE command requires fileID as arguments.')
        continue
    elif split_command[0] == "SCS":
        computationOperations = ['AVERAGE', 'MAX', 'MIN', 'SUM']
        if len(split_command) == 3:
            if split_command[1].isdigit() and split_command[2] in computationOperations:
                server_compute(username, split_command[1], split_command[2])
            else:
                print('the fileID is not an integer or computationOperation is not in [AVERAGE, MAX, MIN, SUM], you need to specify the parameters')
        else:
            print('SCS command requires fileID and computationOperation as arguments')
        continue
    elif split_command[0] == "UED":
        if len(split_command) == 2:
            if split_command[1].isdigit():
                upload_edge_data(username, split_command[1])
            else:
                print('the fileID is not an integer, you need to specify the parameter as integer')
        else:
            print('UED command requires fileID as arguments.')
        continue
    elif split_command[0] == "UVF":
        if len(split_command) == 3:
            uvf(username, split_command[2], split_command[1])
        else:
            print('UVF command requires deviceName and filename as arguments')
        continue
            

    # receive response from the server
    # 1024 is a suggested packet size, you can specify it as 2048 or others
    data = clientSocket.recv(1024)
    receivedMessage = data.decode()

# close the socket
clientSocket.close()
