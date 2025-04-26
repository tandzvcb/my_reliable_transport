import argparse
import socket
import sys
import time
from utils import PacketHeader, compute_checksum
from scapy.all import Raw

def sender(receiver_ip, receiver_port, window_size):
    # Khởi tạo socket UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(0.01)  # Timeout nhỏ để kiểm tra ACK thường xuyên

    # Đọc và chia dữ liệu từ stdin
    message = sys.stdin.buffer.read()
    chunk_size = 1456  # 1472 - 16 (header)
    chunks = [message[i:i + chunk_size] for i in range(0, len(message), chunk_size)]
    total_packets = len(chunks)

    # Gửi gói START
    start_pkt = PacketHeader(type=0, seq_num=0, length=0, checksum=0)
    start_pkt.checksum = compute_checksum(bytes(start_pkt))
    sock.sendto(bytes(start_pkt), (receiver_ip, receiver_port))

    # Chờ ACK cho START
    while True:
        try:
            data, _ = sock.recvfrom(1472)
            ack_pkt = PacketHeader(data)
            temp_ack = PacketHeader(type=ack_pkt.type, seq_num=ack_pkt.seq_num, length=0, checksum=0)
            if (compute_checksum(bytes(temp_ack)) == ack_pkt.checksum and 
                ack_pkt.type == 3 and 
                ack_pkt.seq_num == 0):
                break
        except socket.timeout:
            sock.sendto(bytes(start_pkt), (receiver_ip, receiver_port))

    # Khởi tạo biến cửa sổ trượt
    base = 1
    next_seq_num = 1
    timer_running = False
    timer_start = 0
    packets_sent = {}
    acknowledged = set()

    # Hàm gửi gói tin
    def send_packet(seq_num):
        if seq_num <= total_packets:
            payload = chunks[seq_num - 1]
            pkt = PacketHeader(type=2, seq_num=seq_num, length=len(payload), checksum=0)
            full_pkt = pkt / Raw(payload)
            full_pkt.checksum = compute_checksum(bytes(full_pkt))
            sock.sendto(bytes(full_pkt), (receiver_ip, receiver_port))
            packets_sent[seq_num] = full_pkt
        else:
            end_pkt = PacketHeader(type=1, seq_num=seq_num, length=0, checksum=0)
            end_pkt.checksum = compute_checksum(bytes(end_pkt))
            sock.sendto(bytes(end_pkt), (receiver_ip, receiver_port))
            packets_sent[seq_num] = end_pkt
        return time.time()

    # Vòng lặp chính
    while base <= total_packets + 1:
        # Gửi các gói tin trong cửa sổ
        while next_seq_num < base + window_size and next_seq_num <= total_packets:
            if next_seq_num not in acknowledged:
                last_send_time = send_packet(next_seq_num)
                if not timer_running:
                    timer_start = last_send_time
                    timer_running = True
            next_seq_num += 1

        # Nhận ACK
        try:
            data, _ = sock.recvfrom(1472)
            ack_pkt = PacketHeader(data)
            temp_ack = PacketHeader(type=ack_pkt.type, seq_num=ack_pkt.seq_num, length=0, checksum=0)
            if (compute_checksum(bytes(temp_ack)) == ack_pkt.checksum and 
                ack_pkt.type == 3):
                acknowledged.add(ack_pkt.seq_num)
                # Cập nhật base đến seq_num nhỏ nhất chưa được ACK
                while base in acknowledged and base <= total_packets + 1:
                    base += 1
                # Kiểm tra xem còn gói nào chưa được ACK
                timer_running = any(seq_num not in acknowledged for seq_num in packets_sent)
                if timer_running:
                    timer_start = time.time()
        except socket.timeout:
            pass

        # Xử lý timeout tái truyền
        if timer_running and time.time() - timer_start > 0.5:
            for seq_num in range(base, next_seq_num):
                if seq_num not in acknowledged and seq_num in packets_sent:
                    sock.sendto(bytes(packets_sent[seq_num]), (receiver_ip, receiver_port))
            timer_start = time.time()

    # Xử lý gói END
    end_seq_num = total_packets + 1
    if end_seq_num not in packets_sent:
        send_packet(end_seq_num)
    end_timer_start = time.time()
    while time.time() - end_timer_start < 0.5:
        try:
            data, _ = sock.recvfrom(1472)
            ack_pkt = PacketHeader(data)
            temp_ack = PacketHeader(type=ack_pkt.type, seq_num=ack_pkt.seq_num, length=0, checksum=0)
            if (compute_checksum(bytes(temp_ack)) == ack_pkt.checksum and 
                ack_pkt.type == 3 and 
                ack_pkt.seq_num == end_seq_num):
                break
        except socket.timeout:
            pass

    sock.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RTP Sender")
    parser.add_argument("receiver_ip", help="The IP address of the receiver")
    parser.add_argument("receiver_port", type=int, help="The port number of the receiver")
    parser.add_argument("window_size", type=int, help="Maximum number of outstanding packets")
    args = parser.parse_args()
    sender(args.receiver_ip, args.receiver_port, args.window_size)