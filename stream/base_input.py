import threading
import queue
from abc import ABC, abstractmethod
import logging

class BaseInputProducer(threading.Thread, ABC):
    """
    Abstract Base Class (Template) for all types of Producers.
    Inherits from threading.Thread to run in the background.
    """
    def __init__(self, source_url: str, frame_queue: queue.Queue):
        super().__init__()
        self.source_url = source_url
        self.frame_queue = frame_queue
        self.running = True
        self.daemon = True  # Allows the thread to terminate with the main program.
        self.logger = logging.getLogger("AIPipeline")

    @abstractmethod
    def _connect(self):
        """Forces child classes to implement a connection function."""
        pass

    @abstractmethod
    def run(self):
        """Forces child classes to implement an image retrieval function (runs in a Thread)."""
        pass

    def stop(self):
        """Stop function (common to all, no need to reimplement)."""
        self.running = False
        self.logger.debug(f"[{self.__class__.__name__}] Stop signal received.")