def create_standard_header(data_length, sqn):
    header = create_header(data_length, sqn, 0, 0)

    return header


def create_syn_header(sqn):
    header = create_header(0, sqn, 0, 1)

    return header


def create_syn_ack_header(sqn, response):
    header = create_header(0, sqn, response, 3)

    return header


def create_ack_header(sqn, response):
    header = create_header(0, sqn, response, 2)

    return header


def create_update_ack_header(sqn, response):
    header = create_header(0, sqn, response, 66)

    return header


def create_update_header(sqn):
    header = create_header(0, sqn, 0, 64)

    return header


def create_fin_header(sqn):
    header = create_header(0, sqn, 0, 8)

    return header


def create_fin_ack_header(sqn, response):
    header = create_header(0, sqn, response, 10)

    return header


def get_length(header):
    return int.from_bytes(header[0:2], "big")


def get_sqn(header):
    return int.from_bytes(header[2:6], "big")


def get_response(header):
    return int.from_bytes(header[6:10], "big")


def get_flag(header):
    return int.from_bytes(header[10:11], "big")


def get_checksum(header):
    return int.from_bytes(header[11:15], "big")


def print_header(header):
    length = get_length(header)
    sqn = get_sqn(header)
    response = get_response(header)
    checksum = get_checksum(header)
    flag = get_flag(header)

    print("header: " + str(header))
    print("===========================")
    print("length: " + str(length))
    print("sqn: " + str(sqn))
    print("response: " + str(response))
    print("checksum: " + str(checksum))
    print("flag: " + str(flag))
    print("===========================")


def create_header(data_length, sqn, response, flags):
    header_length = 15
    length = header_length + data_length

    length_bytes = length.to_bytes(2, "big")
    sqn_bytes = sqn.to_bytes(4, "big")
    response_bytes = response.to_bytes(4, "big")
    flags_bytes = flags.to_bytes(1, "big")
    checksum_bytes = (0).to_bytes(4, "big") # will implement later

    header = length_bytes + sqn_bytes + response_bytes + flags_bytes + checksum_bytes

    return header
