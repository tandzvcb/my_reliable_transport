import socket
import sys
import time
from utils import PacketHeader, compute_checksum

MSG_TYPE_START = 0
MSG_TYPE_DATA = 1
MSG_TYPE_END = 2
MSG_TYPE_ACK = 3

def sender(receiver_host, receiver_port, input_file, window_size):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1.0)

    # Đọc dữ liệu đầu vào
    if input_file == "-":
        data = sys.stdin.buffer.read()
    else:
        with open(input_file, 'rb') as f:
            data = f.read()

    chunk_size = 1024
    chunks = [data[i:i+chunk_size] for i in range(0, len(data), chunk_size)]

    # Gửi gói START
    start_pkt = PacketHeader(type=MSG_TYPE_START, seq_num=0, length=0, checksum=0)
    temp_start_bytes = bytes(start_pkt)
    start_pkt.checksum = compute_checksum(temp_start_bytes)
    sock.sendto(bytes(start_pkt), (receiver_host, receiver_port))
    print(f"Sent START | Checksum: {start_pkt.checksum}")

    base = 1  # Bắt đầu từ 1
    next_seq_num = 1  # DATA bắt đầu từ 1
    window = {}

    while base < len(chunks):
        # Gửi các gói trong cửa sổ
        while next_seq_num < base + window_size and next_seq_num < len(chunks):
            payload = chunks[next_seq_num]
            pkt = PacketHeader(
                type=MSG_TYPE_DATA,
                seq_num=next_seq_num,
                length=len(payload),
                checksum=0
            )
            temp_header = bytes(pkt)
            full_packet_temp = temp_header + payload
            pkt.checksum = compute_checksum(full_packet_temp)
            
            final_packet = bytes(pkt) + payload
            sock.sendto(final_packet, (receiver_host, receiver_port))
            window[next_seq_num] = (final_packet, time.time())
            print(f"Sent DATA {next_seq_num} | Checksum: {pkt.checksum}")
            next_seq_num += 1

        # Chờ ACK
        try:
            ack_data, _ = sock.recvfrom(1024)
            ack_pkt = PacketHeader(ack_data[:16])
            
            # Kiểm tra checksum ACK
            temp_ack_header = PacketHeader(
                type=ack_pkt.type,
                seq_num=ack_pkt.seq_num,
                length=ack_pkt.length,
                checksum=0
            )
            calc_checksum = compute_checksum(bytes(temp_ack_header))
            
            if calc_checksum == ack_pkt.checksum:
                print(f"Received ACK {ack_pkt.seq_num}")
                base = ack_pkt.seq_num
            else:
                print(f"Invalid ACK checksum {ack_pkt.checksum}")
                
        except socket.timeout:
            print("Timeout! Resending window...")
            for seq in range(base, min(base + window_size, len(chunks))):
                if seq in window:
                    sock.sendto(window[seq][0], (receiver_host, receiver_port))
                    print(f"Resent packet {seq}")

    # Gửi gói END
    end_pkt = PacketHeader(type=MSG_TYPE_END, seq_num=len(chunks), length=0, checksum=0)
    temp_end_bytes = bytes(end_pkt)
    end_pkt.checksum = compute_checksum(temp_end_bytes)
    sock.sendto(bytes(end_pkt), (receiver_host, receiver_port))
    print(f"Sent END | Checksum: {end_pkt.checksum}")   
    
    # Chờ ACK cho END trong 500ms
    end_time = time.time() + 0.5
    while time.time() < end_time:
        try:
            ack_data, _ = sock.recvfrom(1024)
            ack_pkt = PacketHeader(ack_data[:16])
            temp_ack_header = PacketHeader(
                type=ack_pkt.type,
                seq_num=ack_pkt.seq_num,
                length=ack_pkt.length,
                checksum=0
            )
            calc_checksum = compute_checksum(bytes(temp_ack_header))
            if calc_checksum == ack_pkt.checksum and ack_pkt.type == MSG_TYPE_ACK and ack_pkt.seq_num == len(chunks) + 1:
                print(f"Received ACK {ack_pkt.seq_num} for END")
                break
        except socket.timeout:
            continue

    sock.close()

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python sender.py <receiver_host> <port> <input_file> <window_size>")
        sys.exit(1)
    sender(sys.argv[1], int(sys.argv[2]), sys.argv[3], int(sys.argv[4]))