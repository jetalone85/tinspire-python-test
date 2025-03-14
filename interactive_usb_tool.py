#!/usr/bin/env python3
"""
TI-Nspire CX II-T Interactive Communication Module

This module provides a class-based implementation for interacting with the TI-Nspire CX II-T USB device.
It allows sending hex data packets and logging the responses to both the console and a file.
All comments and log messages are in English.
"""

import logging
import sys
from typing import Optional

import usb.core
import usb.util

# Logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# USB device constants for TI-Nspire CX II-T
TI_VENDOR_ID = 0x0451
TI_PRODUCT_ID = 0xE022
ENDPOINT_IN = 0x81
ENDPOINT_OUT = 0x01
INTERFACE_NUMBER = 0


class TINspireDevice:
    """
    Class to manage interactive communication with the TI-Nspire CX II-T USB device.
    """

    def __init__(self) -> None:
        """
        Initializes the device by detecting, configuring, and claiming its USB interface.
        Exits the program if the device is not found or cannot be properly initialized.
        """
        self.device: Optional[usb.core.Device] = None
        self.initialize_device()

    def initialize_device(self) -> None:
        """
        Detects and initializes the TI-Nspire CX II-T USB device.
        Detaches any active kernel driver, sets the configuration, and claims the interface.
        """
        logging.info("Searching for TI-Nspire CX II-T USB device...")
        self.device = usb.core.find(idVendor=TI_VENDOR_ID, idProduct=TI_PRODUCT_ID)
        if self.device is None:
            logging.error("TI-Nspire device not found.")
            sys.exit(1)

        if self.device.is_kernel_driver_active(INTERFACE_NUMBER):
            try:
                self.device.detach_kernel_driver(INTERFACE_NUMBER)
                logging.info("Kernel driver detached.")
            except usb.core.USBError as e:
                logging.error(f"Error detaching kernel driver: {e}")
                sys.exit(1)

        try:
            self.device.set_configuration()
            usb.util.claim_interface(self.device, INTERFACE_NUMBER)
            logging.info("Device initialized successfully.")
        except usb.core.USBError as e:
            logging.error(f"USB error during initialization: {e}")
            sys.exit(1)

    def send_and_receive(self, data: bytes, timeout_write: int = 2000, timeout_read: int = 3000) -> Optional[bytes]:
        """
        Sends hex data to the device and reads the response.

        Parameters:
            data (bytes): The data packet to send.
            timeout_write (int): Write operation timeout in milliseconds.
            timeout_read (int): Read operation timeout in milliseconds.

        Returns:
            Optional[bytes]: The response from the device, or None if an error occurred.
        """
        logging.info(f"Sending: {data.hex()}")
        try:
            self.device.write(ENDPOINT_OUT, data, timeout=timeout_write)
        except usb.core.USBError as e:
            logging.error(f"USB error during write: {e}")
            return None

        try:
            response = self.device.read(ENDPOINT_IN, 512, timeout=timeout_read)
            response_bytes = bytes(response)
            logging.info(f"Received ({len(response_bytes)} bytes): {response_bytes.hex()}")
            return response_bytes
        except usb.core.USBError as e:
            logging.error(f"USB error during read: {e}")
            return None

    def release(self) -> None:
        """
        Releases the device interface and disposes of allocated resources.
        """
        logging.info("Releasing device resources...")
        try:
            usb.util.release_interface(self.device, INTERFACE_NUMBER)
            usb.util.dispose_resources(self.device)
            logging.info("Device released.")
        except usb.core.USBError as e:
            logging.error(f"Error releasing device: {e}")


def main() -> None:
    """
    Main function that provides an interactive loop for sending hex data packets to the device.
    The sent data and responses are logged to both the console and a file.
    """
    device_manager = TINspireDevice()

    try:
        while True:
            user_input = input("Enter hex data to send (or 'exit' to quit): ").strip()
            if user_input.lower() == 'exit':
                break

            try:
                data = bytes.fromhex(user_input)
            except ValueError:
                logging.error("Invalid hex data. Please try again.")
                continue

            response = device_manager.send_and_receive(data)

            # Log the sent data and received response to a file
            try:
                with open("usb_responses.log", "ab") as log_file:
                    log_file.write(b"Sent: " + data + b"\n")
                    if response is not None:
                        log_file.write(b"Received: " + response + b"\n\n")
                    else:
                        log_file.write(b"Received: None (timeout or error)\n\n")
            except Exception as e:
                logging.error(f"Error writing to log file: {e}")

    except KeyboardInterrupt:
        logging.info("Interrupted by user.")
    finally:
        device_manager.release()


if __name__ == "__main__":
    main()
