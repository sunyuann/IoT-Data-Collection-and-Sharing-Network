"""
    Sample code for Multi-Threaded Server
    Python 3
    Usage: python3 TCPserver3.py localhost 12000
    coding: utf-8
    
    Author: Wei Song (Tutor for COMP3331/9331)
"""
from socket import *
from threading import Thread
import sys, select
from _thread import *
import json
import threading
import random
from datetime import *
import os


########### GLOBAL VARIABLES #################
# active edge device sequence number starts at 1
aed_sequence_number = 1
# num failed attempts, will change to given command line arg when server is started
num_failed_attempts_allowed = 0
# dictionary to keep track of num failed attempts of each user
failed_attempts_users = {}
# dictionary to keep track of blocked users & time blocked
blocked_users = {}


"""
    Define multi-thread class for client
    This class would be used to define the instance for each connection from each client
    For example, client-1 makes a connection request to the server, the server will call
    class (ClientThread) to define a thread for client-1, and when client-2 make a connection
    request to the server, the server will call class (ClientThread) again and create a thread
    for client-2. Each client will be runing in a separate therad, which is the multi-threading
"""
class ClientThread(Thread):
    def __init__(self, clientAddress, clientSocket):
        Thread.__init__(self)
        self.clientAddress = clientAddress
        self.clientSocket = clientSocket
        self.clientAlive = False
        
        print("===== New connection created for: ", clientAddress)
        self.clientAlive = True
        
    def run(self):
        decoded_message = ''
        
        while self.clientAlive:
            # use recv() to receive message from the client
            data = self.clientSocket.recv(1024)
            decoded_data = data.decode()
            data_list = decoded_data.split(" ")
            message = data_list[0]
            
            # if the message from client is empty, the client would be off-line then set the client as offline (alive=False)
            if message == '':
                self.clientAlive = False
                print("===== the user disconnected - ", clientAddress)
                break
            
            # ===============================================
            # handle message from the client
            
            # login case
            if message == 'login':
                print("[recv] New login request")
                username = data_list[1]
                password = data_list[2]
                host = data_list[3]
                port = data_list[4]
                # store credentials into credentials dictionary
                credentials = {}
                with open('credentials.txt') as file:
                    for line in file.readlines():
                        username_password_pairs = line.split(' ')
                        credentials[username_password_pairs[0]] = username_password_pairs[1].strip()
                # blocked case
                if username in blocked_users:
                    curr_time = datetime.now()
                    time_blocked = blocked_users[username]
                    time_remaining_blocked = curr_time - time_blocked
                    if time_remaining_blocked.total_seconds() < 10:
                        message = 'blocked'
                        print("[send] " + message)
                        self.clientSocket.send(message.encode())
                        continue
                    else:
                        blocked_users.pop(username)
                # login successful case
                if username in credentials and password == credentials[username]:
                        message = 'login_successful'
                        print("[send]" + message)
                        self.clientSocket.send(message.encode())
                        print(username + " has logged in")
                        # add login info to edge device log file
                        created_time = datetime.now()
                        edge_device_entry = str(aed_sequence_number) + "; " + created_time.strftime("%d %B %Y %X") + "; " + username + "; " + str(host) + "; " + str(port) + '\n'
                        increment_aed_sequence_number()
                        aed_file = open('edge_device_log.txt', 'a')
                        aed_file.write(edge_device_entry)
                        aed_file.close()
                # login unsuccessful case
                else:
                    if username not in failed_attempts_users:
                        failed_attempts_users[username] = 1
                    else:
                        failed_attempts_users[username] += 1
                    if failed_attempts_users[username] >= num_failed_attempts_allowed:
                        failed_attempts_users.pop(username)
                        blocked_users[username] = datetime.now()
                        message = 'login_fail_blocked'
                        print("[send] " + message)
                        self.clientSocket.send(message.encode())
                    else:
                        message = 'login_failed'
                        print("[send] " + message)
                        self.clientSocket.send(message.encode())
            
            # OUT case
            elif message == 'logout':
                username = data_list[1]
                # remove login info from edge device log file
                with open('edge_device_log.txt', 'r') as filedata:
                    inputFilelines = filedata.readlines()
                    line_index = 1
                    with open('edge_device_log.txt', 'w') as filedata:
                        deleted_line = False
                        for textline in inputFilelines:
                            split_textline = textline.split("; ")
                            if (split_textline[2] == username):
                                deleted_line = True
                            elif (deleted_line):
                                newseqnum_textline = str(line_index) + "; " + split_textline[1] + "; " + split_textline[2]  + "; " + split_textline[3]  + "; " + split_textline[4]  + '\n'
                                filedata.write(newseqnum_textline)
                                line_index += 1
                            else:
                                filedata.write(textline)
                                line_index += 1
                decrement_aed_sequence_number()
                filedata.close()
                # remove excessive newlines at end of file, leaving only one newline
                filedata = open('edge_device_log.txt', 'r+')
                content = filedata.read()
                content = content.rstrip('\n')
                filedata.seek(0)
                filedata.write(content + '\n')
                filedata.truncate()
                filedata.close()
                
                print(username + " exited the edge network")
            
            # AED case
            elif message == 'list_AEDs':
                username = data_list[1]
                print('The edge device ' + username + ' issued AED command')
                print('Return other active edge device list:')
                full_message = ''
                with open('edge_device_log.txt', 'r') as filedata:
                    for textline in filedata.readlines():
                        split_textline = textline.split('; ')
                        if (split_textline[2] != username):
                            message = split_textline[2] + '; ' + split_textline[3] + '; ' + split_textline[4] + '; active since ' + split_textline[1] + '.' 
                            if full_message == '':
                                full_message = message
                            else:
                                full_message = full_message + ' ,,, ' + message
                            print(message)
                filedata.close()
                if full_message == '':
                    final_message = 'NED'
                    self.clientSocket.send(final_message.encode())
                    print('No edge devices')
                else:
                    final_message = full_message
                    self.clientSocket.send(final_message.encode())
            
            # DTE case
            elif message == 'delete_file':
                username = data_list[1]
                fileID = data_list[2]
                fileName = username + '-' + fileID + '.txt'
                print('Edge device ' + username + ' issued DTE command, the file ID is ' + fileID)
                print('Return message')
                if os.path.exists(fileName):
                    # find dataAmount of file
                    dataAmount = 0
                    with open(fileName, 'r') as filedata:
                        for textline in filedata.readlines():
                            dataAmount += 1
                    filedata.close()
                    os.remove(fileName)
                    deleted_time = datetime.now()
                    deletion_log_entry = username + '; ' + deleted_time.strftime("%d %B %Y %X") + '; ' + fileID + '; ' + str(dataAmount) + '\n'
                    f = open('deletion_log.txt', 'a')
                    f.write(deletion_log_entry)
                    f.close()
                    print('The file with ID of ' + fileID + ' from edge device ' + username + ' has been deleted, deletion log file has been updated')
                    message = 'deleted'
                    self.clientSocket.send(message.encode())
                else:
                    message = 'not deleted'
                    self.clientSocket.send(message.encode())
            
            # SCS case
            elif message == 'server_compute':
                username = data_list[1]
                fileID = data_list[2]
                computationOperation = data_list[3]
                fileName = username + '-' + fileID + '.txt'
                print('Edge device ' + username + ' requested a computation operation on the file with ID of ' + fileID)
                if os.path.exists(fileName):
                    dataAmount = 0
                    sum = 0
                    max = -9999999
                    min = 9999999
                    with open(fileName, 'r') as filedata:
                        for textline in filedata.readlines():
                            data = int(textline.rstrip('\n'))
                            dataAmount += 1
                            sum += data
                            if (data > max):
                                max = data
                            if (data < min):
                                min = data
                    filedata.close()
                    average = sum / dataAmount
                    print("Return message")
                    computed_val = -1000
                    if computationOperation == "AVERAGE":
                        computed_val = average
                    elif computationOperation == "MAX":
                        computed_val = max
                    elif computationOperation == "MIN":
                        computed_val = min
                    elif computationOperation == "SUM":
                        computed_val = sum
                    print(computationOperation + ' computation has been made on edge device ' + username + ' data file (ID:' + fileID + '), the result is ' + str(computed_val))
                    message = 'Computation (' + computationOperation + ') result on the file (ID:' + fileID + ') returned from the server is: ' + str(computed_val)
                    self.clientSocket.send(message.encode())
                else:
                    message = 'file (ID:' + fileID + ') does not exist at the server side'
                    print(message)
                    self.clientSocket.send(message.encode())
                
            # UED case, receiving edge data from client
            elif message == 'download_file':
                username = data_list[1]
                fileID = data_list[2]
                dataAmount = data_list[3]
                fileData = data_list[4]
                fileName = username + '-' + fileID + '.txt'
                print('Edge device ' + username + ' issued UED command')
                f = open(fileName, 'w')
                f.write(fileData)
                f.close()
                upload_time = datetime.now()
                upload_log_entry = username + '; ' + upload_time.strftime("%d %B %Y %X") + '; ' + fileID + '; ' + str(dataAmount) + '\n'
                upload_log_file = open('upload_log.txt', 'a')
                upload_log_file.write(upload_log_entry)
                upload_log_file.close()
                
                print('Return message:')
                print('The file with ID of ' + fileID + ' has been received, upload-log.txt file has been updated')
                message = 'server received file'
                self.clientSocket.send(message.encode())
            
            else:
                print("[recv] " + message)
                print("[send] Cannot understand this message")
                message = 'Cannot understand this message'
                self.clientSocket.send(message.encode())
    
    """
        You can create more customized APIs here, e.g., logic for processing user authentication
        Each api can be used to handle one specific function, for example:
        def process_login(self):
            message = 'user credentials request'
            self.clientSocket.send(message.encode())
    """
    def process_login(self):
        message = 'user credentials request'
        print('[send] ' + message)
        self.clientSocket.send(message.encode())

# increments sequence number for aed
def increment_aed_sequence_number():
    global aed_sequence_number
    aed_sequence_number += 1

# decrements sequence number for aed
def decrement_aed_sequence_number():
    global aed_sequence_number
    aed_sequence_number -= 1

# sets global variable for num_failed_attempts_allowed
def set_num_failed_attempts_allowed(num):
    global num_failed_attempts_allowed
    num_failed_attempts_allowed = num
    return

if __name__ == '__main__':
    print("\n===== Server is running =====")
    print("===== Waiting for connection request from clients...=====")
    # acquire server host and port from command line parameter
    if len(sys.argv) != 3:
        print("\n===== Error usage, python3 TCPServer3.py SERVER_PORT NUM_FAILED_ATTEMPTS_ALLOWED ======\n")
        exit(0)
    if (sys.argv[2].isdigit()):
        if (int(sys.argv[2]) < 1 or int(sys.argv[2]) > 5):
            print("Invalid number of allowed failed consecutive attempts: " + sys.argv[2] + ". The valid value of argument number is an integer between 1 and 5")
            exit(0)
    else:
        print("Invalid number of allowed failed consecutive attempts: " + sys.argv[2] + ". The valid value of argument number is an integer between 1 and 5")
        exit(0)
    # set global num failed attempts allowed
    num_failed_attempts_allowed = int(sys.argv[2])
    set_num_failed_attempts_allowed(num_failed_attempts_allowed)
    
    serverHost = "127.0.0.1"
    serverPort = int(sys.argv[1])
    serverAddress = (serverHost, serverPort)
    
    # define socket for the server side and bind address
    serverSocket = socket(AF_INET, SOCK_STREAM)
    serverSocket.bind(serverAddress)
    
    # delete and create new deletion_log.txt file to track deleted files
    deletion_log_file = open('deletion_log.txt', 'w')
    deletion_log_file.close()
    
    # delete and create new upload_log.txt file to track uploaded files
    upload_log_file = open('upload_log.txt', 'w')
    upload_log_file.close()
    
    # delete and create new edge_device_log.txt file to track active edge devices
    edge_device_log_file = open('edge_device_log.txt', 'w')
    edge_device_log_file .close()
    while True:
        serverSocket.listen(5)
        clientSockt, clientAddress = serverSocket.accept()
        clientThread = ClientThread(clientAddress, clientSockt)
        clientThread.start()