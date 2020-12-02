import socket
import threading
import time
import os
import zlib

import random

import udpExtension

serverIP = b''
serverPort = 0

clientIP = b''
clientPort = 0

serverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

DGRAMBufferSize = 65507

updateTimer = 0
updateReceiverOn = False

listenerOpen = False
unacknowledgedQueues = []
lastSentPackets = []
dataBuffer = []
fragmentCount = 0
cur_sqn = 0

mainGUI = None


class Packet:
    def __init__(self, header, data):
        self.header = header
        self.data = data


class DataBufferElement:
    def __init__(self, sqn, data):
        self.sqn = sqn
        self.data = data


def set_gui(main_gui):
    global mainGUI

    mainGUI = main_gui


def set_server_address(server_ip, server_port):
    global serverIP, serverPort

    serverIP = server_ip.encode()
    serverPort = server_port


def set_client_address(client_ip, client_port):
    global clientIP, clientPort

    clientIP = client_ip.encode()
    clientPort = client_port


def bind_socket():
    global serverSocket

    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    serverSocket.bind((serverIP, serverPort))


def start_server_listener():
    global listenerOpen
    listenerOpen = True

    mainGUI.send_message("Server začal počúvať na porte " + serverIP.decode() + ":" + str(serverPort))

    server_listener_thread = threading.Thread(target=server_listener)
    server_listener_thread.start()


def stop_server_listener():
    global listenerOpen

    mainGUI.send_message("Server prestal počúvať na porte " + serverIP.decode() + ":" + str(serverPort))

    listenerOpen = False
    serverSocket.shutdown(socket.SHUT_RDWR)
    serverSocket.close()


def clear_unacknowledged_queues():
    for unacknowledged_queue in unacknowledgedQueues:
        for unacknowledged_packet in unacknowledged_queue:
            unacknowledged_queue.remove(unacknowledged_packet)

        unacknowledgedQueues.remove(unacknowledged_queue)


def server_listener():
    while listenerOpen is True:
        try:
            data, client_address = serverSocket.recvfrom(DGRAMBufferSize)

            global updateTimer, unacknowledgedQueues, fragmentCount
            updateTimer = 0

            data_header = data[:15]
            data_data = data[15:]

            data_header_without_checksum = data_header[:11]
            checksum = zlib.crc32(data_header_without_checksum + data_data)

            """
            print("Server prijal správu:")
            udpExtension.print_header(data_header)
            print("data: " + str(data_data))
            print()
            """

            if udpExtension.get_checksum(data_header) == checksum:
                flag = udpExtension.get_flag(data_header)

                # i got syn, i will save client address and respond with syn-ack
                if flag == 1:
                    set_client_address(client_address[0], client_address[1])
                    mainGUI.set_client_address(clientIP, clientPort)

                    threading.Thread(target=send_to_client_syn_ack).start()
                # i got ack, i will remove unacknowledged syn-ack packet from queue
                # or i will remove unacknowledged fin packet from queue
                # or i will remove unacknowledged standard packet from queue
                elif flag == 2:
                    for unacknowledged_queue in unacknowledgedQueues:
                        for unacknowledged_packet in unacknowledged_queue:
                            unacknowledged_header = unacknowledged_packet.header

                            # response of received packet is equal to sqn of unacknowledged packet
                            if udpExtension.get_sqn(unacknowledged_header) == udpExtension.get_response(data_header):
                                # flag of unacknowledged packet is syn-ack
                                if udpExtension.get_flag(unacknowledged_header) == 3:
                                    unacknowledged_queue.remove(unacknowledged_packet)
                                    if len(unacknowledged_queue) == 0:
                                        unacknowledgedQueues.remove(unacknowledged_queue)

                                    start_update_receiver()
                                # flag of unacknowledged packet is fin-ack
                                elif udpExtension.get_flag(unacknowledged_header) == 10:
                                    close_connection()
                                # flag of unacknowledged packet is standard
                                elif udpExtension.get_flag(unacknowledged_header) == 0:
                                    unacknowledged_queue.remove(unacknowledged_packet)
                # i got update, i will respond with update-ack
                elif flag == 64:
                    send_to_client_update_ack(udpExtension.get_sqn(data_header))
                # i got fin, i will respond with fin-ack
                elif flag == 8:
                    threading.Thread(target=send_to_client_fin_ack, args=[udpExtension.get_sqn(data_header)]).start()
                # i got fin-ack, i will remove unacknowledged fin packet from queue, send ack packet and end connection
                elif flag == 10:
                    for unacknowledged_queue in unacknowledgedQueues:
                        for unacknowledged_packet in unacknowledged_queue:
                            unacknowledged_header = unacknowledged_packet.header

                            # response of received packet is equal to sqn of unacknowledged packet
                            if udpExtension.get_sqn(unacknowledged_header) == udpExtension.get_response(data_header):
                                # flag of unacknowledged packet is fin
                                if udpExtension.get_flag(unacknowledged_header) == 8:
                                    unacknowledged_queue.remove(unacknowledged_packet)
                                    if len(unacknowledged_queue) == 0:
                                        unacknowledgedQueues.remove(unacknowledged_queue)

                                    send_to_client_ack(udpExtension.get_sqn(data_header))

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

                                        filename = mainGUI.fileTransferEntry.get()
                                        path = os.path.abspath("Input/" + filename)
                                        mainGUI.send_message("Súbor bol úspešne odoslaný v " + str(fragmentCount) +
                                                             " paketoch!")
                                        mainGUI.send_message("Odoslaný súbor: " + path)

                                        fragmentCount = 0
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

                                        message = mainGUI.textTransferEntry.get()
                                        mainGUI.send_message("Správa bola úspešne odoslaná v " + str(fragmentCount) +
                                                             " paketoch!")
                                        mainGUI.send_message("Odoslaná správa: " + message)

                                        fragmentCount = 0
                # i got standard packet, i will add data to buffer and respond with ack
                elif flag == 0 and mainGUI.deviceState.get() == "receiver":
                    threading.Thread(target=send_to_client_ack, args=(udpExtension.get_sqn(data_header),)).start()

                    was_received = False
                    for data_buffer_element in dataBuffer:
                        if data_buffer_element.sqn == udpExtension.get_sqn(data_header):
                            was_received = True
                            break

                    if was_received is False:
                        new_data_buffer_element = DataBufferElement(udpExtension.get_sqn(data_header), data_data)
                        dataBuffer.append(new_data_buffer_element)
                # i got last-file, i will respond with last-file-ack and create file from buffer
                elif flag == 144:
                    threading.Thread(target=send_to_client_last_file_ack, args=(udpExtension.get_sqn(data_header),)).start()

                    create_file_from_buffer(data_data.decode())
                # i got last-text, i will respond with last-text-ack and create file from buffer
                elif flag == 160:
                    threading.Thread(target=send_to_client_last_text_ack, args=(udpExtension.get_sqn(data_header),)).start()

                    create_text_from_buffer()
                # i got error, i will resend packet from last sent packets
                elif flag == 4:
                    for sent_packet in lastSentPackets:
                        sent_header = sent_packet.header

                        # response of received packet is equal to sqn of previously sent packet
                        if udpExtension.get_sqn(sent_header) == udpExtension.get_response(data_header):
                            send_to_client(sent_header, sent_packet.data)
            else:
                """
                print("PREDOŠLÁ PRIJATÁ SPRÁVA BOLA CHYBNÁ!")
                print()
                """

                threading.Thread(target=send_to_client_error, args=(udpExtension.get_sqn(data_header),)).start()
        except IOError:
            break


def create_file_from_buffer(filename):
    global dataBuffer

    if len(dataBuffer) == 0:
        return

    received_packets = len(dataBuffer)

    sorted_buffer = sorted(dataBuffer, key=lambda obj: obj.sqn)

    new_file = open(mainGUI.fileReceiveEntry.get() + "/" + filename, 'wb')

    for buffer_element in sorted_buffer:
        new_file.write(buffer_element.data)

    new_file.close()

    path = os.path.abspath(mainGUI.fileReceiveEntry.get() + "/" + filename)

    mainGUI.send_message("Súbor bol úspešne prijatý v " + str(received_packets) + " paketoch!")
    mainGUI.send_message("Prijatý súbor: " + path)

    dataBuffer = []


def create_text_from_buffer():
    global dataBuffer

    if len(dataBuffer) == 0:
        return

    sorted_buffer = sorted(dataBuffer, key=lambda obj: obj.sqn)

    string_list = []
    for buffer_element in sorted_buffer:
        string_list.append(buffer_element.data.decode())

    output_string = ""
    for string in string_list:
        output_string += string

    mainGUI.send_message("Správa bola úspešne prijatá v: " + str(len(sorted_buffer)) + " paketoch!")
    mainGUI.send_message("Prijatá správa: " + output_string)

    dataBuffer = []


def start_update_receiver():
    global updateReceiverOn
    updateReceiverOn = True

    mainGUI.send_message("Server inicializoval spojenie s portom " + clientIP.decode() + ":" + str(clientPort))

    update_receiver_thread = threading.Thread(target=update_receiver)
    update_receiver_thread.start()


def stop_update_receiver():
    global updateReceiverOn

    mainGUI.send_message("Server ukončil spojenie s portom " + clientIP.decode() + ":" + str(clientPort))

    updateReceiverOn = False


def update_receiver():
    global updateTimer

    while updateReceiverOn is True:
        while updateTimer < 20:
            time.sleep(1)
            updateTimer += 1

            if updateReceiverOn is False:
                break

        if updateReceiverOn is True:
            print("ERROR! UPDATE NOT RECEIVED FOR 20 SECONDS!")
            close_connection()


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

            send_to_client(header, data)

    print("ERROR! NO RESPONSE!")

    stop_update_receiver()
    stop_server_listener()
    close_connection()


def send_to_client_fragmented_bytes(remaining_bytes, fragment_size):
    global cur_sqn, unacknowledgedQueues, fragmentCount

    unacknowledged_queue = []
    unacknowledgedQueues.append(unacknowledged_queue)
    queue_size = 10

    error_counter = 0
    max_error_count = 3

    fragmentCount = 0

    while len(remaining_bytes) > 0 or len(unacknowledged_queue) > 0:
        while len(unacknowledged_queue) < queue_size and len(remaining_bytes) > 0:
            if len(remaining_bytes) > fragment_size:
                fragment_data = remaining_bytes[:fragment_size]
                fragment_header = udpExtension.create_standard_header(fragment_data, cur_sqn)

                remaining_bytes = remaining_bytes[fragment_size:]
            else:
                fragment_data = remaining_bytes
                fragment_header = udpExtension.create_standard_header(fragment_data, cur_sqn)

                remaining_bytes = []

            unacknowledged_packet = Packet(fragment_header, fragment_data)
            unacknowledged_queue.append(unacknowledged_packet)
            cur_sqn = udpExtension.inc_sqn(cur_sqn)
            fragmentCount += 1

        for unacknowledged_packet in unacknowledged_queue:
            send_to_client(unacknowledged_packet.header, unacknowledged_packet.data)

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


def send_to_client_file(file_path, fragment_size):
    file_binary = open(file_path, "rb").read()

    head, filename = os.path.split(file_path)

    end_message = send_to_client_fragmented_bytes(file_binary, fragment_size)

    if end_message == "ok":
        threading.Thread(target=send_to_client_last_file, args=(filename,)).start()


def send_to_client_text(text, fragment_size):
    text_bytes = text.encode()

    end_message = send_to_client_fragmented_bytes(text_bytes, fragment_size)

    if end_message == "ok":
        threading.Thread(target=send_to_client_last_text).start()


def send_to_client_last_file(filename):
    global cur_sqn

    filename_bytes = filename.encode()

    header = udpExtension.create_last_file_header(filename_bytes, cur_sqn)

    send_to_client(header, filename_bytes)

    unacknowledged_packet = Packet(header, filename_bytes)
    unacknowledged_queue = [unacknowledged_packet]
    unacknowledgedQueues.append(unacknowledged_queue)

    lastSentPackets.append(unacknowledged_packet)
    if len(lastSentPackets) > 100:
        del lastSentPackets[0]

    threading.Thread(target=wait_for_response, args=(unacknowledged_queue,)).start()

    cur_sqn = udpExtension.inc_sqn(cur_sqn)


def send_to_client_last_text():
    global cur_sqn

    header = udpExtension.create_last_text_header(cur_sqn)

    send_to_client(header, b'')

    unacknowledged_packet = Packet(header, b'')
    unacknowledged_queue = [unacknowledged_packet]
    unacknowledgedQueues.append(unacknowledged_queue)

    lastSentPackets.append(unacknowledged_packet)
    if len(lastSentPackets) > 100:
        del lastSentPackets[0]

    threading.Thread(target=wait_for_response, args=(unacknowledged_queue,)).start()

    cur_sqn = udpExtension.inc_sqn(cur_sqn)


def send_to_client_syn_ack():
    global cur_sqn

    header = udpExtension.create_syn_ack_header(0, 0)

    send_to_client(header, b'')

    unacknowledged_packet = Packet(header, b'')
    unacknowledged_queue = [unacknowledged_packet]
    unacknowledgedQueues.append(unacknowledged_queue)

    lastSentPackets.append(unacknowledged_packet)
    if len(lastSentPackets) > 100:
        del lastSentPackets[0]

    threading.Thread(target=wait_for_response, args=(unacknowledged_queue,)).start()

    cur_sqn = udpExtension.inc_sqn(cur_sqn)


def send_to_client_ack(response):
    global cur_sqn

    header = udpExtension.create_ack_header(cur_sqn, response)

    new_packet = Packet(header, b'')
    send_to_client(new_packet.header, new_packet.data)
    lastSentPackets.append(new_packet)
    if len(lastSentPackets) > 100:
        del lastSentPackets[0]

    cur_sqn = udpExtension.inc_sqn(cur_sqn)


def send_to_client_error(response):
    global cur_sqn

    header = udpExtension.create_error_header(cur_sqn, response)

    new_packet = Packet(header, b'')
    send_to_client(new_packet.header, new_packet.data)
    lastSentPackets.append(new_packet)
    if len(lastSentPackets) > 100:
        del lastSentPackets[0]

    cur_sqn = udpExtension.inc_sqn(cur_sqn)


def send_to_client_last_text_ack(response):
    global cur_sqn

    header = udpExtension.create_last_text_ack_header(cur_sqn, response)

    new_packet = Packet(header, b'')
    send_to_client(new_packet.header, new_packet.data)
    lastSentPackets.append(new_packet)
    if len(lastSentPackets) > 100:
        del lastSentPackets[0]

    cur_sqn = udpExtension.inc_sqn(cur_sqn)


def send_to_client_last_file_ack(response):
    global cur_sqn

    header = udpExtension.create_last_file_ack_header(cur_sqn, response)

    new_packet = Packet(header, b'')
    send_to_client(new_packet.header, new_packet.data)
    lastSentPackets.append(new_packet)
    if len(lastSentPackets) > 100:
        del lastSentPackets[0]

    cur_sqn = udpExtension.inc_sqn(cur_sqn)


def send_to_client_update_ack(response):
    global cur_sqn

    header = udpExtension.create_update_ack_header(cur_sqn, response)

    new_packet = Packet(header, b'')
    send_to_client(new_packet.header, new_packet.data)
    lastSentPackets.append(new_packet)
    if len(lastSentPackets) > 100:
        del lastSentPackets[0]

    cur_sqn = udpExtension.inc_sqn(cur_sqn)


def send_to_client_fin():
    global cur_sqn

    header = udpExtension.create_fin_header(cur_sqn)

    send_to_client(header, b'')

    unacknowledged_packet = Packet(header, b'')
    unacknowledged_queue = [unacknowledged_packet]
    unacknowledgedQueues.append(unacknowledged_queue)

    lastSentPackets.append(unacknowledged_packet)
    if len(lastSentPackets) > 100:
        del lastSentPackets[0]

    threading.Thread(target=wait_for_response, args=(unacknowledged_queue,)).start()

    cur_sqn = udpExtension.inc_sqn(cur_sqn)


def send_to_client_fin_ack(response):
    global cur_sqn

    header = udpExtension.create_fin_ack_header(cur_sqn, response)

    send_to_client(header, b'')

    unacknowledged_packet = Packet(header, b'')
    unacknowledged_queue = [unacknowledged_packet]
    unacknowledgedQueues.append(unacknowledged_queue)

    lastSentPackets.append(unacknowledged_packet)
    if len(lastSentPackets) > 100:
        del lastSentPackets[0]

    threading.Thread(target=wait_for_response, args=(unacknowledged_queue,)).start()

    cur_sqn = udpExtension.inc_sqn(cur_sqn)


messages_till_error_init = 10
messages_till_error = messages_till_error_init


def send_to_client(header, data):
    global messages_till_error

    messages_till_error -= 1

    print("Server poslal správu klientovi:")
    udpExtension.print_header(header)
    print("data: " + str(data))
    print()

    global updateTimer
    updateTimer = 0

    if messages_till_error == 0:
        messages_till_error = messages_till_error_init

        random_num = random.randrange(100)

        if random_num > 50:
            print("PREDOŠLÁ ODOSLANÁ SPRÁVA SA PRI PRENOSE POŠKODILA!")
            print()

            data = "chyba".encode()
        else:
            print("PREDOŠLÁ ODOSLANÁ SPRÁVA SA PRI PRENOSE STRATILA!")
            print()
            
            return

    serverSocket.sendto(header + data, (clientIP, clientPort))


def close_connection():
    global lastSentPackets

    clear_unacknowledged_queues()
    stop_update_receiver()
    stop_server_listener()
    lastSentPackets = []

    mainGUI.set_closed_connection_buttons()
