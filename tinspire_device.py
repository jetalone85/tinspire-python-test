#!/usr/bin/env python3
"""
TI-Nspire CX II-T File Transfer Module

This module provides a class-based implementation to interact with the TI-Nspire CX II-T USB device.
It supports file read and write operations over USB. All comments and log messages are in English.
"""

import logging
import struct
import sys
import usb.core
import usb.util

# Logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


class TINspireDevice:
    # USB and protocol constants
    VENDOR_ID = 0x0451
    PRODUCT_ID = 0xE022
    CONFIGURATION = 1
    INTERFACE = 0
    ENDPOINT_IN = 0x81
    ENDPOINT_OUT = 0x01
    TIMEOUT = 10000

    # Service identifier for file operations
    SERVICE_FILE = 0x4060

    def __init__(self):
        """
        Initialize the TI-Nspire device by finding it on the USB bus.
        Exits the program if the device is not found.
        """
        self.device = usb.core.find(idVendor=self.VENDOR_ID, idProduct=self.PRODUCT_ID)
        if self.device is None:
            logging.error("TI-Nspire not found.")
            sys.exit(1)

    def initialize(self) -> None:
        """
        Initialize the device by detaching any active kernel driver, setting the configuration,
        and claiming the interface.
        """
        if self.device.is_kernel_driver_active(self.INTERFACE):
            self.device.detach_kernel_driver(self.INTERFACE)
            logging.debug("Kernel driver detached.")

        try:
            self.device.set_configuration(self.CONFIGURATION)
            usb.util.claim_interface(self.device, self.INTERFACE)
            logging.info("Device initialized successfully.")
        except usb.core.USBError as e:
            logging.error(f"USB error during initialization: {e}")
            sys.exit(1)

    def write(self, data: bytes) -> None:
        """
        Write data to the device.

        Parameters:
            data (bytes): Data packet to send.
        """
        self.device.write(self.ENDPOINT_OUT, data, timeout=self.TIMEOUT)
        logging.debug(f"Wrote {len(data)} bytes.")

    def read(self, length: int = 512) -> bytes:
        """
        Read data from the device.

        Parameters:
            length (int): Number of bytes to read.

        Returns:
            bytes: The data read from the device.
        """
        response = self.device.read(self.ENDPOINT_IN, length, timeout=self.TIMEOUT)
        logging.debug(f"Read {len(response)} bytes.")
        return bytes(response)

    def build_packet(self, cmd: int, path: str, payload: bytes) -> bytes:
        """
        Build a packet with a command, a null-terminated UTF-8 path, and a payload.

        Parameters:
            cmd (int): Command code.
            path (str): Remote file path.
            payload (bytes): Additional payload.

        Returns:
            bytes: The constructed packet.
        """
        path_encoded = path.encode('utf-8') + b'\x00'
        header = struct.pack(">H", cmd)
        return header + path_encoded + payload

    def connect_service(self, service_id: int) -> None:
        """
        Connect to a specific service on the device by sending its service ID.

        Parameters:
            service_id (int): The service identifier to connect.
        """
        service_packet = struct.pack(">H", service_id)
        self.write(service_packet)
        response = self.read()
        logging.debug(f"Service connected, response: {response.hex()}")

    def disconnect_service(self) -> None:
        """
        Disconnect from the current service.
        """
        disconnect_packet = b'\xff'
        self.write(disconnect_packet)
        logging.debug("Disconnected service.")

    def file_write(self, remote_path: str, file_content: bytes) -> None:
        """
        Upload a file to the TI-Nspire device.

        Parameters:
            remote_path (str): Destination path on the device.
            file_content (bytes): File data to upload.
        """
        logging.info(f"Uploading file to '{remote_path}' ({len(file_content)} bytes).")

        # Connect to file service (SERVICE_FILE)
        self.connect_service(self.SERVICE_FILE)

        # Build the initialization packet for file write (command 0x0301)
        init_packet = self.build_packet(0x0301, remote_path, struct.pack(">I", len(file_content)))
        self.write(init_packet)
        response = self.read()
        logging.debug(f"Response after init_packet: {response.hex()}")

        if response[0] != 0x04:
            raise Exception("Invalid response on file write initialization.")

        # Send file data in chunks of 253 bytes prefixed with header 0x05
        offset = 0
        while offset < len(file_content):
            chunk = file_content[offset:offset + 253]
            packet = bytes([0x05]) + chunk
            self.write(packet)
            offset += len(chunk)
            logging.debug(f"Sent chunk of {len(chunk)} bytes.")

        # Read final response to confirm upload
        final_response = self.read()
        logging.debug(f"Final response after file write: {final_response.hex()}")

        if final_response[-2:] != b'\xff\x00':
            raise Exception("File upload failed or not confirmed by device.")

        # End file service
        self.close_service()
        logging.info("File uploaded successfully.")

    def file_read(self, remote_path: str) -> bytes:
        """
        Download a file from the TI-Nspire device.

        Parameters:
            remote_path (str): Path to the file on the device.

        Returns:
            bytes: The file contents.
        """
        logging.info(f"Reading file '{remote_path}'")

        # Connect to file service
        self.connect_service(self.SERVICE_FILE)

        # Build read command (command 0x0701, followed by path and null-terminator)
        read_packet = struct.pack('>H', 0x0701) + remote_path.encode('utf-8') + b'\x00'
        self.write(read_packet)

        # Read the header response
        header_response = self.read()
        logging.debug(f"Header response: {header_response.hex()}")

        # Validate header response; expecting at least 16 bytes and specific command code
        if len(header_response) < 16 or header_response[:2] != b'\x03\x01':
            self.close_service()
            raise Exception("File doesn't exist or invalid response.")

        file_size = struct.unpack('>I', header_response[12:16])[0]
        logging.info(f"File size to read: {file_size} bytes")

        # Send confirmation to start file transfer
        self.write(b'\x04')

        data_received = bytearray()
        bytes_left = file_size

        # Read file data in packets; each packet begins with a header byte
        while bytes_left > 0:
            # Read header + up to 253 data bytes (total packet size is min(bytes_left + 1, 254))
            chunk_size = min(bytes_left + 1, 254)
            chunk = self.read(chunk_size)
            if not chunk:
                raise Exception("Unexpected timeout during file read.")
            data_chunk = chunk[1:]  # Ignore the header byte
            data_len = len(data_chunk)
            bytes_left -= data_len
            data_received.extend(data_chunk)
            logging.debug(f"Received {data_len} bytes, {bytes_left} bytes remaining")

        # Send final confirmation to complete the transfer
        self.write(struct.pack('>H', 0xFF00))
        self.close_service()
        logging.info("File read successfully.")
        return bytes(data_received)

    def close_service(self) -> None:
        """
        Close the current service session.
        """
        self.device.write(self.ENDPOINT_OUT, b'\x04', timeout=self.TIMEOUT)
        logging.info("Service closed.")

    def close(self) -> None:
        """
        Release the USB interface and dispose of the device resources.
        """
        usb.util.release_interface(self.device, self.INTERFACE)
        usb.util.dispose_resources(self.device)
        logging.info("Device closed properly.")


if __name__ == "__main__":
    device_manager = TINspireDevice()
    try:
        device_manager.initialize()

        # Example: Read a file from the device
        remote_path = "/documents/examples/test.txt"  # File path on the TI-Nspire
        file_content = device_manager.file_read(remote_path)
        logging.info(f"File contents:\n{file_content.decode('utf-8')}")

        # Optionally, save the file locally
        with open("downloaded_from_ti.txt", "wb") as f:
            f.write(file_content)

    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        device_manager.close()
