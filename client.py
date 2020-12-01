import socket
import threading
import time

import udpExtension

serverIP = ""
serverPort = 0

clientIP = ""
clientPort = 0

clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

DGRAMBufferSize = 65507

updateTimer = 0
updateSenderOn = False

listenerOpen = False
unacknowledgedQueues = []
cur_sqn = 0

mainGUI = None


class UnacknowledgedPacket:
    def __init__(self, header, data):
        self.header = header
        self.data = data


def set_gui(main_gui):
    global mainGUI

    mainGUI = main_gui


def set_server_address(server_ip, server_port):
    global serverIP, serverPort

    serverIP = server_ip
    serverPort = server_port


def set_client_address(client_ip, client_port):
    global clientIP, clientPort

    clientIP = client_ip
    clientPort = client_port


def bind_socket():
    global clientSocket

    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
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
    clientSocket.close()


def start_update_sender():
    global updateSenderOn

    if updateSenderOn is False:
        updateSenderOn = True

        update_sender_thread = threading.Thread(target=update_sender)
        update_sender_thread.start()


def stop_update_sender():
    global updateSenderOn
    updateSenderOn = False


def clear_unacknowledged_queues():
    for unacknowledged_queue in unacknowledgedQueues:
        for unacknowledged_packet in unacknowledged_queue:
            unacknowledged_queue.remove(unacknowledged_packet)

        unacknowledgedQueues.remove(unacknowledged_queue)


def update_sender():
    print("KLIENT OTVORIL SPOJENIE")
    print()

    global updateTimer

    while updateSenderOn is True:
        while updateTimer < 10:
            time.sleep(1)
            updateTimer += 1

            if updateSenderOn is False:
                break

        if updateSenderOn is True:
            send_to_server_update()

    print("KLIENT UKONČIL SPOJENIE")
    print()


def client_listener():
    print("KLIENT ZAČAL POČÚVAŤ")
    print()

    while listenerOpen is True:
        try:
            data, server_address = clientSocket.recvfrom(DGRAMBufferSize)

            global updateTimer, unacknowledgedQueues
            updateTimer = 0

            data_header = data[:15]
            data_data = data[15:]

            flag = udpExtension.get_flag(data_header)

            print("Klient prijal správu:")
            udpExtension.print_header(data_header)
            print("data: " + str(data_data))
            print()

            # i got syn-ack, i will remove unacknowledged syn packet from queue
            if flag == 3:
                for unacknowledged_queue in unacknowledgedQueues:
                    for unacknowledged_packet in unacknowledged_queue:
                        unacknowledged_header = unacknowledged_packet.header

                        # response of received packet is equal to sqn of unacknowledged packet
                        if udpExtension.get_sqn(unacknowledged_header) == udpExtension.get_response(data_header):

                            # flag of unacknowledged packet is syn
                            if udpExtension.get_flag(unacknowledged_header) == 1:
                                unacknowledged_queue.remove(unacknowledged_packet)
                                if len(unacknowledged_queue) == 0:
                                    unacknowledgedQueues.remove(unacknowledged_queue)

                    unacknowledged_sqn = udpExtension.get_sqn(data_header)

                    send_to_server_ack(unacknowledged_sqn)
                    start_update_sender()
            # i got update-ack, i will remove unacknowledged update packet from queue
            elif flag == 66:
                for unacknowledged_queue in unacknowledgedQueues:
                    for unacknowledged_packet in unacknowledged_queue:
                        unacknowledged_header = unacknowledged_packet.header

                        # response of received packet is equal to sqn of unacknowledged packet
                        if udpExtension.get_sqn(unacknowledged_header) == udpExtension.get_response(data_header):
                            # flag of unacknowledged packet is update
                            if udpExtension.get_flag(unacknowledged_header) == 64:
                                unacknowledged_queue.remove(unacknowledged_packet)
                                if len(unacknowledged_queue) == 0:
                                    unacknowledgedQueues.remove(unacknowledged_queue)
            # i got ack, i will remove unacknowledged fin packet from queue and end connection
            # or i will remove standard packet from queue
            elif flag == 2:
                for unacknowledged_queue in unacknowledgedQueues:
                    for unacknowledged_packet in unacknowledged_queue:
                        unacknowledged_header = unacknowledged_packet.header

                        # response of received packet is equal to sqn of unacknowledged packet
                        if udpExtension.get_sqn(unacknowledged_header) == udpExtension.get_response(data_header):
                            # flag of unacknowledged packet is fin-ack
                            if udpExtension.get_flag(unacknowledged_header) == 10:
                                close_connection()
                            # flag of unacknowledged packet is standard
                            elif udpExtension.get_flag(unacknowledged_header) == 0:
                                unacknowledged_queue.remove(unacknowledged_packet)
            # i got fin, i will respond with fin-ack
            elif flag == 8:
                threading.Thread(target=send_to_server_fin_ack, args=[udpExtension.get_sqn(data_header)]).start()
            # i got fin-ack, i will remove unacknowledged fin packet from queue, send ack packet and end connection
            elif flag == 10:
                for unacknowledged_queue in unacknowledgedQueues:
                    for unacknowledged_packet in unacknowledged_queue:
                        unacknowledged_header = unacknowledged_packet.header

                        # response of received packet is equal to sqn of unacknowledged packet
                        if udpExtension.get_sqn(unacknowledged_header) == udpExtension.get_response(data_header):
                            # flag of unacknowledged packet is fin
                            if udpExtension.get_flag(unacknowledged_header) == 8:
                                send_to_server_ack(udpExtension.get_sqn(data_header))

                                close_connection()
            # i got last-file-ack, i will remove unacknowledged last-file packet from queue
            elif flag == 146:
                for unacknowledged_queue in unacknowledgedQueues:
                    for unacknowledged_packet in unacknowledged_queue:
                        unacknowledged_header = unacknowledged_packet.header

                        # response of received packet is equal to sqn of unacknowledged packet
                        if udpExtension.get_sqn(unacknowledged_header) == udpExtension.get_response(data_header):
                            # flag of unacknowledged packet is last-file
                            if udpExtension.get_flag(unacknowledged_header) == 144:
                                unacknowledged_queue.remove(unacknowledged_packet)
                                if len(unacknowledged_queue) == 0:
                                    unacknowledgedQueues.remove(unacknowledged_queue)
            # i got last-text-ack, i will remove unacknowledged last-file packet from queue
            elif flag == 162:
                for unacknowledged_queue in unacknowledgedQueues:
                    for unacknowledged_packet in unacknowledged_queue:
                        unacknowledged_header = unacknowledged_packet.header

                        # response of received packet is equal to sqn of unacknowledged packet
                        if udpExtension.get_sqn(unacknowledged_header) == udpExtension.get_response(data_header):
                            # flag of unacknowledged packet is last-text
                            if udpExtension.get_flag(unacknowledged_header) == 160:
                                unacknowledged_queue.remove(unacknowledged_packet)
                                if len(unacknowledged_queue) == 0:
                                    unacknowledgedQueues.remove(unacknowledged_queue)
        except IOError:
            break

    print("KLIENT PRESTAL POČÚVAŤ")
    print()


def wait_for_response(unacknowledged_queue):
    error_count = 0

    while error_count < 3:
        for i in range(5):
            time.sleep(1)
            if len(unacknowledged_queue) == 0:
                return

        error_count += 1

        print("Timeout! Znovu sa posielajú pakety! Error count = " + str(error_count) + ".")

        for unacknowledged_packet in unacknowledged_queue:
            header = unacknowledged_packet.header
            data = unacknowledged_packet.data

            send_to_server(header, data)

    print("ERROR! NO RESPONSE!")

    stop_update_sender()
    stop_client_listener()
    close_connection()


def send_to_server_fragmented_bytes(remaining_bytes, fragment_size):
    global cur_sqn, unacknowledgedQueues

    unacknowledged_queue = []
    unacknowledgedQueues.append(unacknowledged_queue)
    queue_size = 10

    error_counter = 0
    max_error_count = 3

    while len(remaining_bytes) > 0 or len(unacknowledged_queue) > 0:
        while len(unacknowledged_queue) < queue_size and len(remaining_bytes) > 0:
            if len(remaining_bytes) > fragment_size:
                fragment_header = udpExtension.create_standard_header(fragment_size, cur_sqn)
                fragment_data = remaining_bytes[:fragment_size]

                remaining_bytes = remaining_bytes[fragment_size:]
            else:
                fragment_header = udpExtension.create_standard_header(len(remaining_bytes), cur_sqn)
                fragment_data = remaining_bytes

                remaining_bytes = []

            unacknowledged_packet = UnacknowledgedPacket(fragment_header, fragment_data)
            unacknowledged_queue.append(unacknowledged_packet)
            cur_sqn += 1

        for unacknowledged_packet in unacknowledged_queue:
            send_to_server(unacknowledged_packet.header, unacknowledged_packet.data)

        for i in range(5):
            time.sleep(1)
            if len(unacknowledged_queue) == 0:
                break

        # if no response from any sent packet is received 4 times in a row, end connection
        if len(unacknowledged_queue) == queue_size:
            error_counter += 1
            print("ERROR! NO RESPONSE! ERROR_COUNTER - " + str(error_counter))

            if error_counter > max_error_count:
                print("ERROR! NO RESPONSE! MAX ERROR COUNT REACHED!")
                close_connection()
                return "error"
        else:
            error_counter = 0

    unacknowledgedQueues.remove(unacknowledged_queue)

    return "ok"


def send_to_server_file(filename, fragment_size):
    file_binary = open("Input/" + filename, "rb").read()

    end_message = send_to_server_fragmented_bytes(file_binary, fragment_size)

    if end_message == "ok":
        threading.Thread(target=send_to_server_last_file, args=(filename,)).start()


def send_to_server_text(text, fragment_size):
    text_bytes = text.encode()

    end_message = send_to_server_fragmented_bytes(text_bytes, fragment_size)

    if end_message == "ok":
        threading.Thread(target=send_to_server_last_text).start()


def send_to_server_last_file(filename):
    global cur_sqn

    filename_bytes = filename.encode()

    header = udpExtension.create_last_file_header(len(filename_bytes), cur_sqn)

    send_to_server(header, filename_bytes)

    unacknowledged_packet = UnacknowledgedPacket(header, filename_bytes)
    unacknowledged_queue = [unacknowledged_packet]
    unacknowledgedQueues.append(unacknowledged_queue)

    threading.Thread(target=wait_for_response, args=(unacknowledged_queue,)).start()

    cur_sqn += 1


def send_to_server_last_text():
    global cur_sqn

    header = udpExtension.create_last_text_header(cur_sqn)

    send_to_server(header, b'')

    unacknowledged_packet = UnacknowledgedPacket(header, b'')
    unacknowledged_queue = [unacknowledged_packet]
    unacknowledgedQueues.append(unacknowledged_queue)

    threading.Thread(target=wait_for_response, args=(unacknowledged_queue,)).start()

    cur_sqn += 1


def send_to_server_ack(response):
    global cur_sqn

    header = udpExtension.create_ack_header(cur_sqn, response)

    send_to_server(header, b'')

    cur_sqn += 1


def send_to_server_syn():
    global cur_sqn

    header = udpExtension.create_syn_header(cur_sqn)

    send_to_server(header, b'')

    unacknowledged_packet = UnacknowledgedPacket(header, b'')
    unacknowledged_queue = [unacknowledged_packet]
    unacknowledgedQueues.append(unacknowledged_queue)

    threading.Thread(target=wait_for_response, args=(unacknowledged_queue,)).start()

    cur_sqn += 1


def send_to_server_update():
    global cur_sqn

    header = udpExtension.create_update_header(cur_sqn)

    send_to_server(header, b'')

    unacknowledged_packet = UnacknowledgedPacket(header, b'')
    unacknowledged_queue = [unacknowledged_packet]
    unacknowledgedQueues.append(unacknowledged_queue)

    threading.Thread(target=wait_for_response, args=(unacknowledged_queue,)).start()

    cur_sqn += 1


def send_to_server_fin():
    global cur_sqn

    header = udpExtension.create_fin_header(cur_sqn)

    send_to_server(header, "")

    unacknowledged_packet = UnacknowledgedPacket(header, b'')
    unacknowledged_queue = [unacknowledged_packet]
    unacknowledgedQueues.append(unacknowledged_queue)

    threading.Thread(target=wait_for_response, args=(unacknowledged_queue,)).start()

    cur_sqn += 1


def send_to_server_fin_ack(response):
    global cur_sqn

    header = udpExtension.create_fin_ack_header(cur_sqn, response)

    send_to_server(header, "")

    unacknowledged_packet = UnacknowledgedPacket(header, b'')
    unacknowledged_queue = [unacknowledged_packet]
    unacknowledgedQueues.append(unacknowledged_queue)

    threading.Thread(target=wait_for_response, args=(unacknowledged_queue,)).start()

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

    clientSocket.sendto(header + data, (serverIP, serverPort))


def close_connection():
    clear_unacknowledged_queues()
    stop_client_listener()
    stop_update_sender()

    mainGUI.set_closed_connection_buttons()
