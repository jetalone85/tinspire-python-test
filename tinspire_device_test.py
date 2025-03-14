#!/usr/bin/env python3
"""
TI-Nspire CX II-T Basic USB Communication Module

This module demonstrates basic USB communication with the TI-Nspire CX II-T device.
It includes methods to initialize the device, send and receive data, and close the connection.
All comments and log messages are in English.
"""

import logging
import sys

import usb.core
import usb.util

# Logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)


class TINspireDevice:
    """
    Class for basic USB communication with the TI-Nspire CX II-T device.
    """
    VENDOR_ID = 0x0451
    PRODUCT_ID = 0xE022
    CONFIGURATION = 1
    INTERFACE = 0
    ENDPOINT_IN = 0x81
    ENDPOINT_OUT = 0x01
    TIMEOUT = 10000

    def __init__(self) -> None:
        """
        Initialize the TINspireDevice instance.
        """
        self.device = None

    def initialize(self) -> None:
        """
        Detect and initialize the TI-Nspire CX II-T device.
        Exits the program if the device is not found.
        """
        logging.info("Initializing TI-Nspire CX II-T...")
        self.device = usb.core.find(idVendor=self.VENDOR_ID, idProduct=self.PRODUCT_ID)
        if self.device is None:
            logging.error("TI-Nspire CX II-T not found.")
            sys.exit(1)

        # Detach kernel driver if active (required on some platforms)
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
        Send data to the device.

        Parameters:
            data (bytes): Data packet to send.
        """
        logging.info(f"Sending {len(data)} bytes to device.")
        try:
            written = self.device.write(self.ENDPOINT_OUT, data, timeout=self.TIMEOUT)
            logging.debug(f"Wrote {written} bytes.")
        except usb.core.USBError as e:
            logging.error(f"Error while writing: {e}")
            raise

    def read(self, length: int = 512) -> bytes:
        """
        Read data from the device.

        Parameters:
            length (int): Maximum number of bytes to read.

        Returns:
            bytes: The data read from the device.
        """
        logging.info(f"Reading up to {length} bytes from device.")
        try:
            response = self.device.read(self.ENDPOINT_IN, length, timeout=self.TIMEOUT)
            response_bytes = bytes(response)
            logging.debug(f"Read {len(response_bytes)} bytes: {response_bytes.hex()}")
            return response_bytes
        except usb.core.USBError as e:
            logging.error(f"Error while reading: {e}")
            return b""

    def close(self) -> None:
        """
        Release the device interface and dispose of device resources.
        """
        usb.util.release_interface(self.device, self.INTERFACE)
        usb.util.dispose_resources(self.device)
        logging.info("Device closed properly.")


def main() -> None:
    """
    Main function demonstrating basic communication with the TI-Nspire CX II-T device.
    """
    ti_device = TINspireDevice()
    try:
        ti_device.initialize()

        # Example: send a test command (hex value 0x01)
        test_command = bytes.fromhex("01")
        ti_device.write(test_command)

        # Read response from the device
        response = ti_device.read()
        if response:
            logging.info(f"Device responded: {response.hex()}")
        else:
            logging.info("No response received from the device.")
    finally:
        ti_device.close()


if __name__ == "__main__":
    main()
