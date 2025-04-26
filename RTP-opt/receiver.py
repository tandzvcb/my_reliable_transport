import argparse
import socket
import sys
from utils import PacketHeader, compute_checksum

def receiver(receiver_ip, receiver_port, window_size):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((receiver_ip, receiver_port))

    in_connection = False
    expected_seq_num = 0
    buffer = {}
    delivered = []

    def send_ack(seq_num, addr):
        ack_pkt = PacketHeader(type=3, seq_num=seq_num, length=0, checksum=0)
        ack_pkt.checksum = compute_checksum(bytes(ack_pkt))
        sock.sendto(bytes(ack_pkt), addr)

    while True:
        data, addr = sock.recvfrom(1472)
        pkt = PacketHeader(data)
        payload = bytes(pkt.payload) if pkt.type == 2 else b''

        # Xác minh checksum
        saved_checksum = pkt.checksum
        pkt.checksum = 0
        if compute_checksum(bytes(pkt)) != saved_checksum:
            continue

        if not in_connection:
            if pkt.type == 0 and pkt.seq_num == 0:  # START
                in_connection = True
                expected_seq_num = 1
                send_ack(0, addr)
        else:
            if pkt.type == 2:  # DATA
                if pkt.seq_num >= expected_seq_num + window_size:
                    continue
                if pkt.seq_num == expected_seq_num:
                    delivered.append(payload)
                    expected_seq_num += 1
                    while expected_seq_num in buffer:
                        delivered.append(buffer.pop(expected_seq_num))
                        expected_seq_num += 1
                elif pkt.seq_num > expected_seq_num:
                    buffer[pkt.seq_num] = payload
                send_ack(pkt.seq_num, addr)
            elif pkt.type == 1:  # END
                send_ack(pkt.seq_num, addr)
                if pkt.seq_num == expected_seq_num:
                    break
                else:
                    send_ack(pkt.seq_num, addr)

    # Xuất dữ liệu đã nhận
    for data in delivered:
        sys.stdout.buffer.write(data)
    sock.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RTP Receiver")
    parser.add_argument("receiver_ip", help="The IP address to bind to")
    parser.add_argument("receiver_port", type=int, help="The port number to listen on")
    parser.add_argument("window_size", type=int, help="Maximum number of outstanding packets")
    args = parser.parse_args()
    receiver(args.receiver_ip, args.receiver_port, args.window_size)