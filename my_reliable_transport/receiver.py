import socket
import sys
from utils import PacketHeader, compute_checksum

MSG_TYPE_START = 0
MSG_TYPE_DATA = 1
MSG_TYPE_END = 2
MSG_TYPE_ACK = 3

def receiver(port, output_file):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", port))
    print(f"Listening on port {port}")

    expected_seq = 0
    buffer = {}
    received_data = []

    while True:
        data, addr = sock.recvfrom(2048)
        if len(data) < 16:
            continue
            
        header = PacketHeader(data[:16])
        payload = data[16:]

        # Kiểm tra checksum
        if header.type in [MSG_TYPE_START, MSG_TYPE_END, MSG_TYPE_ACK]:
            # Tạo header tạm với checksum=0
            temp_header = PacketHeader(
                type=header.type,
                seq_num=header.seq_num,
                length=header.length,
                checksum=0
            )
            calc_checksum = compute_checksum(bytes(temp_header))
        else:
            # Đối với DATA, tính cả payload
            temp_header = PacketHeader(
                type=header.type,
                seq_num=header.seq_num,
                length=header.length,
                checksum=0
            )
            full_packet_temp = bytes(temp_header) + payload
            calc_checksum = compute_checksum(full_packet_temp)

        if calc_checksum != header.checksum:
            print(f"Bad checksum | Expected: {header.checksum} | Actual: {calc_checksum}")
            continue

        # Xử lý gói tin
        if header.type == MSG_TYPE_START:
            print("Connection started")
            expected_seq = 1
            buffer.clear()
            received_data.clear()

        elif header.type == MSG_TYPE_DATA:
            print(f"Received DATA {header.seq_num}")
            if header.seq_num >= expected_seq:
                buffer[header.seq_num] = payload

            # Gộp dữ liệu theo thứ tự
            while expected_seq in buffer:
                received_data.append(buffer.pop(expected_seq))
                expected_seq += 1

            # Gửi ACK
            ack_pkt = PacketHeader(
                type=MSG_TYPE_ACK,
                seq_num=expected_seq,
                length=0,
                checksum=0
            )   
            ack_bytes = bytes(ack_pkt)
            ack_pkt.checksum = compute_checksum(ack_bytes)
            sock.sendto(bytes(ack_pkt), addr)
            print(f"Sent ACK {expected_seq}")

        elif header.type == MSG_TYPE_END:
            print("Transmission complete")
            break

    # Ghi file đầu ra
    with open(output_file, 'wb') as f:
        f.write(b"".join(received_data))
    print(f"File saved: {output_file}")
    sock.close()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python receiver.py <port> <output_file>")
        sys.exit(1)
    receiver(int(sys.argv[1]), sys.argv[2])