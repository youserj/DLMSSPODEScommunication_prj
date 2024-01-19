from abc import ABC, abstractmethod


class Base(ABC):
    """Common interface for all Media components. Using this interface GXCommunication library enables communication with different medias."""
    inactivity_timeout: int
    INACTIVITY_TIMEOUT_DEFAULT: int = 120
    """in sec"""
    DISCOVERY_TIMEOUT_DEFAULT: int = 10
    """in sec"""
    OCTET_TIMEOUT_DEFAULT: float = 1.0
    """in sec"""

    def __init__(self,
                 inactivity_timeout: int,
                 octet_timeout: float = OCTET_TIMEOUT_DEFAULT):
        self.inactivity_timeout = inactivity_timeout
        self.octet_timeout = octet_timeout

    @abstractmethod
    def __repr__(self):
        """return all properties for restore"""

    @abstractmethod
    def open(self):
        """Opens the media."""

    @abstractmethod
    def is_open(self):
        """Checks if the connection is established. Returns True, if the connection is established."""

    @abstractmethod
    def close(self):
        """Closes the active connection."""

    @abstractmethod
    def send(self, data: bytes, receiver=None):
        """Sends data asynchronously. No reply from the receiver, whether or not the operation was successful, is expected.
        data : Data to send to the device.
        receiver : Media depend information of the receiver (optional)."""

    @abstractmethod
    def receive(self, buf: bytearray) -> bool:
        """ Receive new data synchronously from the media. Result in p.reply. Return True if new data is received. """
