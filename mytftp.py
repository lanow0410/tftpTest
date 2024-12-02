#!/usr/bin/python3
import os
import sys
import socket
import argparse
from struct import pack, unpack

DEFAULT_PORT = 69
BLOCK_SIZE = 512
DEFAULT_TRANSFER_MODE = 'octet'

OPCODE = {'RRQ': 1, 'WRQ': 2, 'DATA': 3, 'ACK': 4, 'ERROR': 5}

ERROR_CODE = {
    0: "Not defined, see error message (if any).",
    1: "File not found.",
    2: "Access violation.",
    3: "Disk full or allocation exceeded.",
    4: "Illegal TFTP operation.",
    5: "Unknown transfer ID.",
    6: "File already exists.",
    7: "No such user."
}



# Timeout and retries settings
SOCKET_TIMEOUT = 5  # seconds
MAX_RETRIES = 3

# Parse command line arguments
parser = argparse.ArgumentParser(description='TFTP client program with timeout.')
parser.add_argument(dest="host", help="Server IP address", type=str)
parser.add_argument(dest="operation", help="get or put a file", type=str)
parser.add_argument(dest="filename", help="name of file to transfer", type=str)
parser.add_argument("-p", "--port", dest="port", type=int, default=DEFAULT_PORT)
args = parser.parse_args()

# Create a UDP socket
server_ip = args.host
server_port = args.port
server_address = (server_ip, server_port)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(SOCKET_TIMEOUT)

operation = args.operation.lower()
filename = args.filename
mode = DEFAULT_TRANSFER_MODE

# Utility functions
def send_rrq(filename, mode, sock, server_address):
    """Send Read Request (RRQ) to the server."""
    format = f'>h{len(filename)}sB{len(mode)}sB'
    rrq_message = pack(format, OPCODE['RRQ'], bytes(filename, 'utf-8'), 0, bytes(mode, 'utf-8'), 0)
    sock.sendto(rrq_message, server_address)

def send_wrq(filename, mode, sock, server_address):
    """Send Write Request (WRQ) to the server."""
    format = f'>h{len(filename)}sB{len(mode)}sB'
    wrq_message = pack(format, OPCODE['WRQ'], bytes(filename, 'utf-8'), 0, bytes(mode, 'utf-8'), 0)
    sock.sendto(wrq_message, server_address)

def send_ack(seq_num, sock, server):
    """Send Acknowledgment (ACK) for the received block."""
    ack_message = pack('>hh', OPCODE['ACK'], seq_num)
    sock.sendto(ack_message, server)


if operation == "get":
    send_rrq(filename, mode, sock, server_address)
elif operation == "put":
    send_wrq(filename, mode, sock, server_address)
else:
    print("Invalid operation. Use 'get' or 'put'.")
    sys.exit(1)

# File download (GET)
if operation == "get":
    try:
        file = open(filename, 'wb')
        expected_block_number = 1
        retries = 0

        while True:
            try:
                data, server_new_socket = sock.recvfrom(516)
                opcode = int.from_bytes(data[:2], 'big')

                if opcode == OPCODE['DATA']:
                    block_number = int.from_bytes(data[2:4], 'big')
                    file_block = data[4:]

                    if block_number == expected_block_number:
                        send_ack(block_number, sock, server_new_socket)
                        file.write(file_block)
                        print(f"Received block {block_number}")
                        expected_block_number += 1
                        retries = 0  # Reset retries on successful data block

                    if len(file_block) < BLOCK_SIZE:
                        print("File transfer completed.")
                        break

                elif opcode == OPCODE['ERROR']:
                    error_code = int.from_bytes(data[2:4], 'big')
                    print(f"Error from server: {ERROR_CODE.get(error_code, 'Unknown error')}")
                    break

            except socket.timeout:
                retries += 1
                if retries > MAX_RETRIES:
                    print("Max retries reached. Aborting transfer.")
                    break
                print(f"Timeout waiting for block {expected_block_number}. Retrying... ({retries}/{MAX_RETRIES})")
                send_rrq(filename, mode, sock, server_address)

    finally:
        file.close()

elif operation == "put":
    try:
        file = open(filename, 'rb')  # 파일을 읽기 모드로 열기
    except FileNotFoundError:
        print(f"파일을 찾을 수 없습니다: {filename}")
        sys.exit(1)

    block_number = 1
    retries = 0  # 재전송 횟수
    MAX_RETRIES = 5  # 최대 재전송 횟수

    file_block = '0'
    data_message = pack(f'>hh{len(file_block)}s', OPCODE['DATA'], block_number, file_block)
    sock.sendto(data_message, server_address)
    print(f"보낸 데이터 블록: {block_number} (크기: {len(file_block)} 바이트)")

    while True:
        # 파일에서 512바이트 읽기
        file_block = file.read(BLOCK_SIZE)
        if not file_block:  # 파일을 모두 읽은 경우
            print("모든 데이터 블록 전송 완료.")
            break

        # DATA 메시지 생성 및 전송
        data_message = pack(f'>hh{len(file_block)}s', OPCODE['DATA'], block_number, file_block)
        sock.sendto(data_message, server_address)
        print(f"보낸 데이터 블록: {block_number} (크기: {len(file_block)} 바이트)")

        while True:
            try:
                # ACK 메시지 수신
                sock.settimeout(5)  # 타임아웃 설정 (5초)
                ack_data, server_new_socket = sock.recvfrom(4)
                opcode, ack_block_number = unpack('>hh', ack_data)

                if opcode == OPCODE['ACK'] and ack_block_number == block_number:
                    print(f"ACK 수신 (블록 {block_number})")
                    block_number += 1
                    retries = 0  # 재전송 횟수 초기화
                    break  # 다음 블록으로 이동
                else:
                    print(f"잘못된 ACK 수신: {ack_block_number}. 블록 {block_number} 재전송.")

            except socket.timeout:
                retries += 1
                if retries > MAX_RETRIES:
                    print("최대 재전송 횟수를 초과했습니다. 파일 전송 실패.")
                    file.close()
                    sys.exit(1)
                print(f"타임아웃 발생. 데이터 블록 {block_number} 재전송 중...")
                sock.sendto(data_message, server_address)

    file.close()
    print("파일 전송 완료.")
