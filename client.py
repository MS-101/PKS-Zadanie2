import socket

serverAddress = ""
clientAddress = ""

clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

DGRAMBufferSize = 65507


def set_server_address(server_address):
    global serverAddress
    serverAddress = server_address


def open_socket():
    global clientSocket

    clientSocket.bind(clientAddress)

    while True:
        data, client_address = clientSocket.recvfrom(DGRAMBufferSize)

        print("Klient prijal správu:")
        print("data: " + str(data))
        print("client_address: " + client_address)


def send_to_server(data):
    print("Klient posiela správu serveru:")
    print("data: " + str(data))
    print("server_address: " + str(serverAddress))

    clientSocket.sendto(data.encode(), serverAddress)


def close_socket():
    global clientSocket

    clientSocket.close()
