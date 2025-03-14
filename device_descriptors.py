#!/usr/bin/env python3
"""
TI-Nspire CX II-T USB Communication Module

This module provides a class-based implementation for detecting, initializing,
retrieving descriptors from, communicating with, and releasing a TI-Nspire CX II-T USB device.
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
    Class to manage the TI-Nspire CX II-T USB device.
    Provides functionalities for device detection, configuration, descriptor logging,
    data transmission, response reading, and resource cleanup.
    """

    def __init__(self) -> None:
        """
        Initializes the device by detecting and configuring it.
        Exits the program if the device cannot be found or configured.
        """
        self.device: Optional[usb.core.Device] = None
        self.initialize_device()

    def initialize_device(self) -> None:
        """
        Detects the TI-Nspire CX II-T USB device, configures it, and claims its interface.
        """
        logging.info("Searching for TI-Nspire CX II-T USB device...")
        self.device = usb.core.find(idVendor=TI_VENDOR_ID, idProduct=TI_PRODUCT_ID)
        if self.device is None:
            logging.error("TI-Nspire CX II-T not found.")
            sys.exit(1)

        logging.info(
            f"TI-Nspire CX II-T found: Vendor ID={hex(self.device.idVendor)}, Product ID={hex(self.device.idProduct)}")

        try:
            # Detach kernel driver if active (necessary for macOS/Linux)
            if self.device.is_kernel_driver_active(INTERFACE_NUMBER):
                self.device.detach_kernel_driver(INTERFACE_NUMBER)
                logging.info("Kernel driver detached.")

            self.device.set_configuration()
            usb.util.claim_interface(self.device, INTERFACE_NUMBER)
            logging.info("Device initialized and interface claimed successfully.")
        except usb.core.USBError as e:
            logging.error(f"USB error during initialization: {e}")
            sys.exit(1)

    def log_descriptors(self) -> None:
        """
        Retrieves and logs basic descriptors from the USB device.
        """
        logging.info("Retrieving device descriptors...")
        try:
            # Device details
            logging.info(f"Vendor ID: {hex(self.device.idVendor)}")
            logging.info(f"Product ID: {hex(self.device.idProduct)}")
            logging.info(f"Device Class: {hex(self.device.bDeviceClass)}")
            logging.info(f"Device Subclass: {hex(self.device.bDeviceSubClass)}")
            logging.info(f"Device Protocol: {hex(self.device.bDeviceProtocol)}")

            # Retrieve manufacturer, product, and serial number strings
            manufacturer = usb.util.get_string(self.device, self.device.iManufacturer)
            product = usb.util.get_string(self.device, self.device.iProduct)
            serial_number = usb.util.get_string(self.device, self.device.iSerialNumber)

            logging.info(f"Manufacturer: {manufacturer}")
            logging.info(f"Product: {product}")
            logging.info(f"Serial Number: {serial_number}")

            # Loop through configurations, interfaces, and endpoints
            for cfg in self.device:
                logging.info(f"Configuration: {cfg.bConfigurationValue}")
                for intf in cfg:
                    logging.info(
                        f" Interface: Number={intf.bInterfaceNumber}, Class={hex(intf.bInterfaceClass)}, "
                        f"SubClass={hex(intf.bInterfaceSubClass)}, Protocol={hex(intf.bInterfaceProtocol)}"
                    )
                    for ep in intf:
                        logging.info(
                            f"  Endpoint: Address={hex(ep.bEndpointAddress)}, Attributes={hex(ep.bmAttributes)}, "
                            f"Max Packet Size={ep.wMaxPacketSize}"
                        )
        except usb.core.USBError as e:
            logging.error(f"Error retrieving device descriptors: {e}")
        except Exception as e:
            logging.error(f"Unexpected error while retrieving descriptors: {e}")

    def send_data(self, data: bytes, timeout: int = 2000) -> None:
        """
        Sends a data packet to the device.

        Parameters:
            data (bytes): The data packet to send.
            timeout (int): Timeout for the write operation in milliseconds.
        """
        logging.info(f"Sending data to device: {data}")
        try:
            bytes_written = self.device.write(ENDPOINT_OUT, data, timeout=timeout)
            logging.info(f"Successfully wrote {bytes_written} bytes.")
        except usb.core.USBError as e:
            logging.error(f"Error sending data: {e}")

    def read_response(self, length: int = 512, timeout: int = 3000) -> None:
        """
        Reads a response from the device.

        Parameters:
            length (int): Maximum number of bytes to read.
            timeout (int): Timeout for the read operation in milliseconds.
        """
        logging.info("Attempting to read response from device...")
        try:
            response = self.device.read(ENDPOINT_IN, length, timeout=timeout)
            logging.info(f"Response received ({len(response)} bytes): {response}")
        except usb.core.USBError as e:
            logging.error(f"Error reading data: {e}")

    def release(self) -> None:
        """
        Releases the device interface and cleans up allocated resources.
        """
        logging.info("Releasing device and cleaning resources...")
        usb.util.release_interface(self.device, INTERFACE_NUMBER)
        usb.util.dispose_resources(self.device)
        logging.info("Device released successfully.")


def main() -> None:
    """
    Main function demonstrating device detection, descriptor retrieval, and communication.
    """
    # Initialize the TI-Nspire device manager
    device_manager = TINspireDevice()

    # Optionally log device descriptors
    if input("Log device descriptors? (y/n): ").strip().lower() in ("y", "yes"):
        device_manager.log_descriptors()

    # Optionally send example data and read response
    if input("Send example data packet to device? (y/n): ").strip().lower() in ("y", "yes"):
        example_data = b'\x00\x01\x02'
        device_manager.send_data(example_data)
        device_manager.read_response()

    # Optionally release the device resources
    if input("Release device resources? (y/n): ").strip().lower() in ("y", "yes"):
        device_manager.release()


if __name__ == "__main__":
    main()
