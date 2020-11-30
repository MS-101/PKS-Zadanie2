import socket
import threading
import udpExtension
import time

serverIP = ""
serverPort = 0

clientIP = ""
clientPort = 0

serverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

DGRAMBufferSize = 65507

updateTimer = 0
updateReceiverOn = False

listenerOpen = False
unacknowledgedQueue = []
cur_sqn = 0


class UnacknowledgedPacket:
    def __init__(self, header, data):
        self.header = header
        self.data = data


def set_server_address(server_ip, server_port):
    global serverIP, serverPort

    serverIP = server_ip
    serverPort = server_port


def set_client_address(client_ip, client_port):
    global clientIP, clientPort

    clientIP = client_ip
    clientPort = client_port


def bind_socket():
    serverSocket.bind((serverIP, serverPort))


def start_server_listener():
    global listenerOpen
    listenerOpen = True

    server_listener_thread = threading.Thread(target=server_listener)
    server_listener_thread.start()


def stop_server_listener():
    global listenerOpen

    listenerOpen = False
    serverSocket.shutdown(socket.SHUT_RDWR)


def server_listener():
    print("SERVER ZAČAL POČÚVAŤ")
    print()

    while listenerOpen is True:
        try:
            data, client_address = serverSocket.recvfrom(DGRAMBufferSize)

            global updateTimer
            updateTimer = 0

            data_header = data[:15]
            data_data = data[15:]

            flag = udpExtension.get_flag(data_header)

            print("Server prijal správu:")
            udpExtension.print_header(data_header)
            print("data: " + data_data.decode())
            print("client_address: " + str(client_address[0]) + ":" + str(client_address[1]))
            print()

            # when receiving syn, save client address and send synack
            if flag == 1:
                global clientIP, clientPort

                clientIP = client_address[0]
                clientPort = client_address[1]

                threading.Thread(target=send_to_client_synack).start()
            # i got ack, i will remove unacknowledged standard packet from queue
            elif flag == 2:
                for unacknowledged_packet in unacknowledgedQueue:
                    unacknowledged_header = unacknowledged_packet.header

                    # response of received packet is equal to sqn of unacknowledged packet
                    if udpExtension.get_sqn(unacknowledged_header) == udpExtension.get_response(data_header):

                        # flag of unacknowledged packet is synack
                        if udpExtension.get_flag(unacknowledged_header) == 3:
                            unacknowledgedQueue.remove(unacknowledged_packet)
                            start_update_receiver()
            # when receiving update, respond with flag, ack
            elif flag == 64:
                send_to_client_updateack(udpExtension.get_sqn(data_header))

        except IOError:
            break

    print("SERVER PRESTAL POČÚVAŤ")
    print()


def start_update_receiver():
    global updateReceiverOn
    updateReceiverOn = True

    update_receiver_thread = threading.Thread(target=update_receiver)
    update_receiver_thread.start()


def stop_update_receiver():
    global updateReceiverOn

    updateReceiverOn = False


def update_receiver():
    print("SERVER ZAČAL PRIJÍMANIE UPDATOV")
    print()

    global updateTimer

    while updateReceiverOn is True:
        while updateTimer < 20:
            time.sleep(1)
            updateTimer += 1

            if updateReceiverOn is False:
                return

        if updateReceiverOn is True:
            print("ERROR! UPDATE NOT RECEIVED FOR 20 SECONDS!")
            close_socket()

    print("SERVER SKONČIL PRIJÍMANIE UPDATOV")
    print()


def wait_for_ack():
    error_count = 0

    while error_count < 3:
        for i in range(5):
            time.sleep(1)
            if len(unacknowledgedQueue) == 0:
                return

        error_count += 1

        print("Timeout! Znovu sa posielajú pakety! Error count = " + str(error_count) + ".")

        for unacknowledged_packet in unacknowledgedQueue:
            header = unacknowledged_packet.header
            data = unacknowledged_packet.data

            send_to_client(header, data)

    print("ERROR! NO RESPONSE!")

    stop_update_receiver()
    stop_server_listener()
    close_socket()


def send_to_client_synack():
    global cur_sqn

    header = udpExtension.create_synack_header(0, 0)

    send_to_client(header, "")

    if len(unacknowledgedQueue) == 0:
        unacknowledged_packet = UnacknowledgedPacket(header, "")
        unacknowledgedQueue.append(unacknowledged_packet)

    threading.Thread(target=wait_for_ack).start()

    cur_sqn = 1


def send_to_client_updateack(response):
    global cur_sqn

    header = udpExtension.create_updateack_header(cur_sqn, response)

    send_to_client(header, "")

    cur_sqn += 1


def send_to_client(header, data):
    print("Server posiela správu klientovi:")
    udpExtension.print_header(header)
    print("data: " + str(data))
    print("client_address: " + clientIP + ":" + str(clientPort))
    print()

    serverSocket.sendto(header + data.encode(), (clientIP, clientPort))


def close_socket():
    stop_server_listener()
    stop_update_receiver()
    serverSocket.close()
