import binascii

from scapy.all import Packet, IntField


class PacketHeader(Packet):
    name = "PacketHeader"
    fields_desc = [
        IntField("type", 0),
        IntField("seq_num", 0),
        IntField("length", 0),
        IntField("checksum", 0),
    ]

def compute_checksum(data):
    return binascii.crc32(data) & 0xFFFFFFFF