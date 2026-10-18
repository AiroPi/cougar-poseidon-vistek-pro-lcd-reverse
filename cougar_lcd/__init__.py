import usb.core
import usb.util
import usb.backend.libusb1
import json
import time
import math
import struct
from datetime import datetime
from typing import Any, BinaryIO, Literal
from enum import Enum
from pathlib import Path


# VID and PID found using lsusb (ex: 0x0c45 0x1234)
ID_VENDOR = 0x1D6B
ID_PRODUCT = 0x0110

class FileType(Enum):
    OSD = 0x01  # Just PNG for overlay
    PNG = 0x02
    MP4 = 0x03  # not sure

FILE_TYPE_EXTENSIONS = {
    FileType.OSD: ".osd",
    FileType.PNG: ".png",
    FileType.MP4: ".mp4",
}

class Response:
    """
    Response from the display. Tries to convert the response as text if printed.
    """
    def __init__(self, value: bytearray):
        self.raw = value

    def __str__(self):
        hex_data = ''.join([f'{x:02x}' for x in self.raw])
        
        try:
            return ''.join([chr(x) for x in self.raw if 32 <= x <= 126])
        except:
            return "Non-text"

class CougarLCD:
    """
    Main class to connect to the device and send packets.

    Example:
        cougar_lcd = CougarLCD()
        cougar_lcd.connect()
        cougar_lcd.resume()
        cougar_lcd.send_png("demo.png")
    """
    def __init__(self, id_vendor: int = ID_VENDOR, id_product: int = ID_PRODUCT):
        self._id_vendor = id_vendor
        self._id_product = id_product

        self._packets_count_value = -1
        self._images_count_value = -1

        self._connect()

    @property
    def _packets_count(self):
        """
        Auto incremented packet counter
        """
        self._packets_count_value += 1
        return self._packets_count_value

    @property
    def _images_count(self):
        """
        Auto incremented image counter
        """
        self._images_count_value = (self._images_count_value + 1 ) % 256
        return self._images_count_value

    def _connect(self):
        self._dev = dev = usb.core.find(idVendor=self._id_vendor, idProduct=self._id_product)
        if dev is None:
            raise RuntimeError("Error: device not found. Check VID/PID.")
    
        if dev.is_kernel_driver_active(0):
            try:
                dev.detach_kernel_driver(0)
                print("Kernel driver detached.")
            except usb.core.USBError as e:
                print(f"Unable to detach the kernel: {str(e)}")
    
        dev.set_configuration()
        
        cfg = dev.get_active_configuration()

        intf = cfg[(0,0)]
        self._ep_out = ep_out = usb.util.find_descriptor(
            intf,
            custom_match = lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
        )
        self._ep_in = ep_in = usb.util.find_descriptor(
            intf,
            custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
        )

        if ep_in is None:
            raise RuntimeError("Error : this device doesn't have return channel (Endpoint IN).")
        
        if ep_out is None:
            raise RuntimeError("Error : endpoint out not found")


    @staticmethod
    def build_request_packet(seq_number: int, method: str, command: str, json_content: dict | None = None):
        """
        Method to build a packet with json data (including checksum, etc...).
        """
        PREFIX = b"\x5a"
        SUFFIX = b"\x5a"
    
        headers = {
            "SeqNumber": str(seq_number),
            "Date": str(int(time.time() * 1000)),
        }
    
        if json_content:
            data_dump = json.dumps(json_content, separators=(',', ':'))
            data = data_dump.encode('utf-8')
            headers["ContentType"] = "json"
            headers["ContentLength"] = str(len(data))
        else:
            data = b""
    
        
        command_bytes = f"{method} {command}".encode("utf-8")  # "POST conn 1"
        headers_lines = ("=".join(c) for c in headers.items())  # SeqNumber=1
        headers_bytes = "\r\n".join(headers_lines).encode("utf-8")
    
        packet_content = command_bytes + b"\r\n" + headers_bytes + 2 * b"\r\n" + data  # assemble the payload
        length_bytes = (len(packet_content) + 5).to_bytes(2, byteorder="big")  # count the size
    
        checksum = sum(length_bytes + packet_content) % 256  # calculate simple checksum
    
        # Build the packet
        packet = PREFIX
        packet += length_bytes
        packet += packet_content
        packet += checksum.to_bytes()
        packet += SUFFIX
   
        # Add trailing null bytes to make 1024 bytes
        if len(packet) < 1024:
            packet += b'\x00' * (1024 - len(packet))
            
        return packet

    @staticmethod
    def file_to_packets(data: BinaryIO, file_type: FileType, file_number: int):
        """
        Method to build packets with file data.
        May requires to split the file in multiple packets of 1024 bytes.
        Supported files types are OSD (PNG as overlay), PNG and MP4.
        """
        raw_data = data.read()
        file_size = len(raw_data)

        PACKET_SIZE = 1024
        HEADER_SIZE = 24
        PAYLOAD_CAPACITY = PACKET_SIZE - HEADER_SIZE

        packets = []
    
        total_data_len = len(raw_data)
        num_packets = math.ceil(total_data_len / PAYLOAD_CAPACITY)
        
        print(f"Processing file ({total_data_len} bytes) into {num_packets} packets.")
    
        for i in range(num_packets):
            start = i * PAYLOAD_CAPACITY
            end = start + PAYLOAD_CAPACITY
            chunk = raw_data[start:end]
            
            chunk_len = len(chunk)
            
            valid_data_len = HEADER_SIZE + chunk_len
            length_field_val = valid_data_len - 3  # prefix and length bytes not counted (= 3 bytes)
            
            # Big Endian '>'
            # B = unsigned char (1 byte)
            # H = unsigned short (2 bytes)
            # 15x = 15 pad bytes (zeros)
            header = struct.pack(
                '>B H B H H B 15x',
                0x5c,              # Prefix
                length_field_val,  # Length field
                file_number,       # Input Num
                num_packets,       # Total Packets
                i,                 # Packet number
                file_type.value    # Fixed Byte
            )
            
            packet_data = header + chunk
            
            # Add trailing zeros...
            if len(packet_data) < PACKET_SIZE:
                padding_needed = PACKET_SIZE - len(packet_data)
                packet_data += b'\x00' * padding_needed
                
            packets.append(packet_data)
    
        return packets, file_size

    def read(self, timeout: int = 1000):
        """
        Read data sent by the display
        """
        try:
            data = self._dev.read(self._ep_in.bEndpointAddress, self._ep_in.wMaxPacketSize, timeout=timeout)
            
            if data:
                return Response(data)
        except usb.core.USBError as e:
            if e.errno == 110:  # Error 110 = Timeout
                pass 
            else:
                print(f"Error: {e}")

    def send_packet(self, method: str, command: str, content: dict | None = None, reply: bool = True):
        """
        Send a command (optionnaly with json) to the display
        """
        pkt = self.build_request_packet(self._packets_count, method, command, content)
        self._ep_out.write(pkt)

        if reply:
            return self.read()

    def send_file(self, path, filetype: FileType):
        """
        Send a file the the display
        """
        if isinstance(path, (str, Path)):
            with open(path, "rb") as f:
                packets, file_size = self.file_to_packets(f, filetype, self._images_count)
        else:
            packets, file_size = self.file_to_packets(path, filetype, self._images_count)

    
        now = datetime.now()
        str_time = now.strftime("%Y-%m-%d_%H-%M-%S")
        millis = now.strftime("%f")[:3]
        filename = f"{str_time}-{millis}{FILE_TYPE_EXTENSIONS[filetype]}"
    
        json_content = {"type": "media", "fileSize": file_size, "fileName": filename}
        print(self.send_packet("POST", "transport 1", json_content))

        for pkt in packets:
            self._ep_out.write(pkt)
        self.read()
    
        json_content = {"md5": "todo", "fileName": filename}
        self.send_packet("POST", "transported 1", json_content)

    def send_png(self, path):
        """
        send_file with PNG
        """
        return self.send_file(path, FileType.PNG)

    def send_osd(self, path):
        """
        send_file with OSD
        """
        return self.send_file(path, FileType.OSD)

    def connect(self):
        """
        Connect to the display (send connect command)
        """
        return self.send_packet("POST", "conn 1")

    def resume(self):
        """
        Send a resume command
        """
        return self.send_packet("POST", "power 1", {"event": "resume"})

    def rotate(self, degree: Literal[0, 90, 180, 270]):
        """
        Rotate the content
        """
        return self.send_packet("POST", "rotate 1", {"degree": degree})


def main():
    cougar_lcd = CougarLCD()
    cougar_lcd.connect()
    cougar_lcd.resume()
    cougar_lcd.send_png("demo.png")

if __name__ == "__main__":
    main()
