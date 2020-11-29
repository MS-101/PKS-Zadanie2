import socket

serverAddress = ""
clientAddress = ""

serverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

DGRAMBufferSize = 65507


def set_server_address(server_address):
    global serverAddress
    serverAddress = server_address


def open_socket():
    global serverSocket, serverAddress, DGRAMBufferSize

    serverSocket.bind(serverAddress)

    while True:
        data, client_address = serverSocket.recvfrom(DGRAMBufferSize)

        print("Server prijal správu:")
        print("data: " + str(data.decode()))
        print("client_address: " + str(client_address))


def send_to_client(data):
    print("Server posiela správu serveru:")
    print("data: " + str(data))
    print("client_address: " + str(clientAddress))

    serverSocket.sendto(data.encode(), serverAddress)


def close_socket():
    global serverSocket

    serverSocket.close()
