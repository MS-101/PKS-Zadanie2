import socket
import threading
import udpExtension
import time

serverIP = ""
serverPort = 0

clientIP = ""
clientPort = 0

clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

DGRAMBufferSize = 65507

updateTimer = 0
updateSenderOn = False

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
    clientSocket.bind((clientIP, clientPort))


def start_client_listener():
    global listenerOpen
    listenerOpen = True

    client_listener_thread = threading.Thread(target=client_listener)
    client_listener_thread.start()


def stop_client_listener():
    global listenerOpen
    listenerOpen = False

    clientSocket.shutdown(socket.SHUT_RDWR)


def start_update_sender():
    global updateSenderOn

    if updateSenderOn is False:
        updateSenderOn = True

        update_sender_thread = threading.Thread(target=update_sender)
        update_sender_thread.start()


def stop_update_sender():
    global updateSenderOn
    updateSenderOn = False


def update_sender():
    print("KLIENT ZAČAL POSIELANIE UPDATOV")
    print()

    global updateTimer

    while updateSenderOn is True:
        while updateTimer < 10:
            time.sleep(1)
            updateTimer += 1

            if updateSenderOn is False:
                return

        if updateSenderOn is True:
            send_to_server_update()

    print("KLIENT SKONČIL POSIELANIE UPDATOV")
    print()


def client_listener():
    print("KLIENT ZAČAL POČÚVAŤ")
    print()

    while listenerOpen is True:
        try:
            data, server_address = clientSocket.recvfrom(DGRAMBufferSize)

            global updateTimer, unacknowledgedQueue
            updateTimer = 0

            data_header = data[:15]
            data_data = data[15:]

            flag = udpExtension.get_flag(data_header)

            print("Klient prijal správu:")
            udpExtension.print_header(data_header)
            print("data: " + data_data.decode())
            print()

            # i got syn-ack, i will remove unacknowledged syn packet from queue
            if flag == 3:
                for unacknowledged_packet in unacknowledgedQueue:
                    unacknowledged_header = unacknowledged_packet.header

                    # response of received packet is equal to sqn of unacknowledged packet
                    if udpExtension.get_sqn(unacknowledged_header) == udpExtension.get_response(data_header):

                        # flag of unacknowledged packet is syn
                        if udpExtension.get_flag(unacknowledged_header) == 1:
                            unacknowledgedQueue.remove(unacknowledged_packet)

                unacknowledged_sqn = udpExtension.get_sqn(data_header)

                send_to_server_ack(unacknowledged_sqn)
                start_update_sender()
            # i got update-ack, i will remove unacknowledged update packet from queue
            elif flag == 66:
                for unacknowledged_packet in unacknowledgedQueue:
                    unacknowledged_header = unacknowledged_packet.header

                    # response of received packet is equal to sqn of unacknowledged packet
                    if udpExtension.get_sqn(unacknowledged_header) == udpExtension.get_response(data_header):
                        # flag of unacknowledged packet is update
                        if udpExtension.get_flag(unacknowledged_header) == 64:
                            unacknowledgedQueue.remove(unacknowledged_packet)
            # i got ack, i will remove unacknowledged fin packet from queue and end connection
            # or i will remove standard packet from queue
            elif flag == 2:
                for unacknowledged_packet in unacknowledgedQueue:
                    unacknowledged_header = unacknowledged_packet.header

                    # response of received packet is equal to sqn of unacknowledged packet
                    if udpExtension.get_sqn(unacknowledged_header) == udpExtension.get_response(data_header):
                        # flag of unacknowledged packet is fin-ack
                        if udpExtension.get_flag(unacknowledged_header) == 10:
                            unacknowledgedQueue.remove(unacknowledged_packet)

                            unacknowledgedQueue = []
                            stop_client_listener()
                            stop_update_sender()
                            close_socket()
                        # flag of unacknowledged packet is standard
                        elif udpExtension.get_flag(unacknowledged_header) == 0:
                            unacknowledgedQueue.remove(unacknowledged_packet)
            # i got fin, i will respond with fin-ack
            elif flag == 8:
                threading.Thread(target=send_to_server_fin_ack, args=[udpExtension.get_sqn(data_header)]).start()
            # i got fin-ack, i will remove unacknowledged fin packet from queue, send ack packet and end connection
            elif flag == 10:
                for unacknowledged_packet in unacknowledgedQueue:
                    unacknowledged_header = unacknowledged_packet.header

                    # response of received packet is equal to sqn of unacknowledged packet
                    if udpExtension.get_sqn(unacknowledged_header) == udpExtension.get_response(data_header):
                        # flag of unacknowledged packet is fin
                        if udpExtension.get_flag(unacknowledged_header) == 8:
                            unacknowledgedQueue.remove(unacknowledged_packet)
                            send_to_server_ack(udpExtension.get_sqn(data_header))

                            unacknowledgedQueue = []
                            stop_client_listener()
                            stop_update_sender()
                            close_socket()
        except IOError:
            break

    print("KLIENT PRESTAL POČÚVAŤ")
    print()


def wait_for_response():
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

            send_to_server(header, data)

    print("ERROR! NO RESPONSE!")

    stop_update_sender()
    stop_client_listener()
    close_socket()


def send_to_server_ack(response):
    global cur_sqn

    header = udpExtension.create_ack_header(cur_sqn, response)

    send_to_server(header, "")

    cur_sqn += 1


def send_to_server_syn():
    global cur_sqn

    header = udpExtension.create_syn_header(cur_sqn)

    send_to_server(header, "")

    unacknowledged_packet = UnacknowledgedPacket(header, "")
    unacknowledgedQueue.append(unacknowledged_packet)

    threading.Thread(wait_for_response()).start()

    cur_sqn += 1


def send_to_server_update():
    global cur_sqn

    header = udpExtension.create_update_header(cur_sqn)

    send_to_server(header, "")

    unacknowledged_packet = UnacknowledgedPacket(header, "")
    unacknowledgedQueue.append(unacknowledged_packet)

    threading.Thread(wait_for_response()).start()

    cur_sqn += 1


def send_to_server_fin():
    global cur_sqn

    header = udpExtension.create_fin_header(cur_sqn)

    send_to_server(header, "")

    unacknowledged_packet = UnacknowledgedPacket(header, "")
    unacknowledgedQueue.append(unacknowledged_packet)

    threading.Thread(wait_for_response()).start()

    cur_sqn += 1


def send_to_server_fin_ack(response):
    global cur_sqn

    header = udpExtension.create_fin_ack_header(cur_sqn, response)

    send_to_server(header, "")

    unacknowledged_packet = UnacknowledgedPacket(header, "")
    unacknowledgedQueue.append(unacknowledged_packet)

    threading.Thread(wait_for_response()).start()

    cur_sqn += 1


def send_to_server(header, data):
    print("Klient poslal správu serveru:")
    udpExtension.print_header(header)
    print("data: " + str(data))
    print("server_address: " + serverIP + ":" + str(serverPort))
    print()

    global cur_sqn
    cur_sqn += 1

    global updateTimer
    updateTimer = 0

    clientSocket.sendto(header + data.encode(), (serverIP, serverPort))


def close_socket():
    global clientSocket

    clientSocket.close()
