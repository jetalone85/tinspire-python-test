#!/usr/bin/env python3
"""
TI-Nspire CX II-T Directory Listing Module

This module provides a class-based implementation to interact with the TI-Nspire CX II-T
USB device. It supports connecting to the file service and listing directory contents.
All comments and log messages are in English.
"""

import logging
import struct
import sys

import usb.core
import usb.util

# Logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


class TINspireDevice:
    """
    Class for interacting with the TI-Nspire CX II-T device over USB.
    """
    VENDOR_ID = 0x0451
    PRODUCT_ID = 0xE022
    CONFIGURATION = 1
    INTERFACE = 0
    ENDPOINT_IN = 0x81
    ENDPOINT_OUT = 0x01
    TIMEOUT = 10000

    # Service identifier for file operations
    SERVICE_FILE = 0x4060

    def __init__(self) -> None:
        """
        Locate the TI-Nspire device on the USB bus.
        Exits the program if the device is not found.
        """
        self.device = usb.core.find(idVendor=self.VENDOR_ID, idProduct=self.PRODUCT_ID)
        if self.device is None:
            logging.error("TI-Nspire not found.")
            sys.exit(1)

    def initialize(self) -> None:
        """
        Initialize the device by detaching any active kernel driver,
        setting the configuration, and claiming the USB interface.
        """
        if self.device.is_kernel_driver_active(self.INTERFACE):
            self.device.detach_kernel_driver(self.INTERFACE)
            logging.debug("Kernel driver detached.")
        self.device.set_configuration(self.CONFIGURATION)
        usb.util.claim_interface(self.device, self.INTERFACE)
        logging.info("Device initialized successfully.")

    def write(self, data: bytes) -> None:
        """
        Send data to the device.

        Parameters:
            data (bytes): Data packet to send.
        """
        self.device.write(self.ENDPOINT_OUT, data, timeout=self.TIMEOUT)
        logging.debug(f"Wrote {len(data)} bytes.")

    def read(self, length: int = 512) -> bytes:
        """
        Read data from the device.

        Parameters:
            length (int): Maximum number of bytes to read.

        Returns:
            bytes: Data read from the device.
        """
        response = bytes(self.device.read(self.ENDPOINT_IN, length, timeout=self.TIMEOUT))
        logging.debug(f"Read {len(response)} bytes: {response.hex()}")
        return response

    def connect_service(self) -> None:
        """
        Connect to the file service on the device by sending its service ID.
        """
        packet = struct.pack('>H', self.SERVICE_FILE)
        self.write(packet)
        self.read()  # Read and ignore service response

    def disconnect_service(self) -> None:
        """
        Disconnect from the current service.
        """
        self.write(b'\x04')
        logging.debug("Service disconnected.")

    def list_directory(self, path: str = "/") -> list:
        """
        List the contents of a directory on the device.

        Parameters:
            path (str): Directory path on the device.

        Returns:
            list: A list of dictionaries, each representing a file or directory.
        """
        logging.info(f"Listing directory: {path}")
        self.connect_service()

        # Build command according to libnspire specification: 0x0D + path + NULL terminator.
        packet = bytes([0x0D]) + path.encode('utf-8') + b'\x00'
        self.write(packet)

        # Read initial status response (should be short, e.g., 2 bytes)
        response = self.read()
        logging.debug(f"Initial response: {response.hex()}")

        files = []
        while True:
            # Request the next directory entry with command 0x0E
            self.write(b'\x0E')
            entry = self.read()

            # Check for end-of-directory marker
            if entry[0] == 0xFF:
                logging.debug("End of directory entries.")
                break

            # Decode directory entry:
            # entry[1]   : entry type (non-zero indicates directory)
            # entry[4:8] : file size (big-endian unsigned int)
            # entry[8:12]: file date (big-endian unsigned int)
            # entry[12:] : filename (null-terminated)
            entry_type = entry[1]
            size = struct.unpack('>I', entry[4:8])[0]
            # Date value is extracted but not used here:
            date = struct.unpack('>I', entry[8:12])[0]
            name_end = entry.find(b'\x00', 12)
            filename = entry[12:name_end].decode('utf-8')

            files.append({
                'name': filename,
                'size': size,
                'type': 'dir' if entry_type else 'file'
            })
            logging.debug(f"Found: {filename}, size: {size}, type: {'dir' if entry_type else 'file'}")

        self.disconnect_service()
        logging.info("Directory listing completed.")
        return files

    def close(self) -> None:
        """
        Release the USB interface and dispose of the device resources.
        """
        usb.util.release_interface(self.device, self.INTERFACE)
        usb.util.dispose_resources(self.device)
        logging.info("Device closed properly.")


def main() -> None:
    """
    Main function to initialize the device and list the contents of the root directory.
    """
    ti_device = TINspireDevice()
    try:
        ti_device.initialize()
        directory_items = ti_device.list_directory("/")
        for item in directory_items:
            entry_type = "DIR" if item['type'] == 'dir' else "FILE"
            print(f"{entry_type}: {item['name']} – {item['size']} bytes")
    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        ti_device.close()


if __name__ == "__main__":
    main()
