import os
import sys
import socket
import argparse
from struct import pack
from struct import unpack

DEFAULT_PORT = 69
BLOCK_SIZE = 128
DEFAULT_TRANSFER_MODE = 'octet'

OPCODE = {'RRQ': 1, 'WRQ': 2, 'DATA': 3, 'ACK': 4, 'ERROR': 5}
MODE = {'netascii': 1, 'octet': 2, 'mail': 3}

ERROR_CODE = {
    0: "Not defined, see error message (if any)",
    1: "File not found.",
    2: "Access violation.",
    3: "Disk full or allocation exceeded.",
    4: "Illegal TFTP operation.",
    5: "Unknown transfer ID.",
    6: "File already exists.",
    7: "No such user."
}

# WRQ 보내는 함수
def send_wrq(filename, mode):
    format = f'>h{len(filename)}sB{len(mode)}sB'
    wrq_message = pack(format, OPCODE['WRQ'], bytes(filename, 'utf-8'), 0, bytes(mode, 'utf-8'), 0)
    sock.sendto(wrq_message, server_address)

def send_rrq(filename, mode):
    format = f'>h{len(filename)}sB{len(mode)}sB'
    rrq_message = pack(format, OPCODE['RRQ'], bytes(filename, 'utf-8'), 0, bytes(mode, 'utf-8'), 0)
    sock.sendto(rrq_message, server_address)
    # print(rrq_message)


def send_ack(seq_num, server):
    format = f'>hh'
    ack_message = pack(format, OPCODE['ACK'], seq_num)
    sock.sendto(ack_message, server)
    print(seq_num)
    print(ack_message)

parser = argparse.ArgumentParser(description='TFTP client program')
parser.add_argument(dest="host", help="Server IP address", type=str)
parser.add_argument(dest="operation", help="get or put a file", type=str)
parser.add_argument(dest="filename", help="name of file to transfer", type=str)
parser.add_argument("-p", "--port", dest="port", type=int)
args = parser.parse_args()


# UDP 소켓
server_ip = args.host
server_port = DEFAULT_PORT
server_address = (server_ip, server_port)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# 타임아웃 설정 (5초)
sock.settimeout(5)

mode = DEFAULT_TRANSFER_MODE
operation = args.operation
filename = args.filename


# RRQ or WRQ 전송
if operation == "get":
    send_rrq(filename, mode)
elif operation == "put":
    send_wrq(filename, mode)

while True:

    if operation == "get":
        file = open(filename, 'wb')
        expected_block_number = 1
        try:
            data, server_new_socket = sock.recvfrom(516)
            opcode = int.from_bytes(data[:2], 'big')

            # check message type
            if opcode == OPCODE['DATA']:
                block_number = int.from_bytes(data[2:4], 'big')
                if block_number == expected_block_number:
                    send_ack(block_number, server_new_socket)
                    file_block = data[4:]
                    file.write(file_block)
                    expected_block_number = expected_block_number + 1
                    print(file_block.decode())
                else:
                    send_ack(block_number, server_new_socket)

            elif opcode == OPCODE['ERROR']:
                error_code = int.from_bytes(data[2:4], byteorder='big')
                print(ERROR_CODE[error_code])
                file.close()
                os.remove(filename)
                break

            else:
                break

            if len(file_block) < BLOCK_SIZE:
                file.close()
                # print(len(file_block))
                print("File transfer completed")
                break

        except socket.timeout:
            print("Timeout waiting for data from server.")
            file.close()
            break

    if operation == "put":
        file = open(filename, 'rb')
        block_number = 1

    while True:
        file_block = file.read(BLOCK_SIZE)
        if not file_block:
            break

        data_message = pack(f'>hh{len(file_block)}s', OPCODE['DATA'], block_number, file_block)
        sock.sendto(data_message, server_address)
        print(f"Sent block {block_number} of size {len(file_block)}bytes")

        try:
            data, server_new_socket = sock.recvfrom(4)
            opcode, ack_block_number = unpack('>hh', data)

            if opcode == OPCODE['ACK']:
                print(f"Received ACK for block {block_number}")
                block_number += 1
            else:
                print(f"Unexpected ACK received: opcode ={opcode}, block_number={ack_block_number}.")
                sock.sendto(data_message, server_address)

        except socket.timeout:
            print(f"Timeout waiting for ACK for block {block_number}. Retrying...")
            sock.sendto(data_message, server_address)

    file.close()
    print("File transfer completed")
    break


sys.exit(0)