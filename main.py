#!/usr/bin/env python3
"""Reference main for a multithreaded service."""

import threading
from time import sleep
import signal
import logging
import os

try:
    import hjson
    PARSE = hjson.loads
except ImportError:
    import json
    PARSE = json.loads


class Main:
    """Main service object for multi-threaded applications."""
    config = {}
    dying = False
    logger = None
    monitored_thread_types = []
    possible_config_files = ['./config.hjson', '/etc/config.hjson']

    def __init__(self):
        """Set up logging and signal handling."""
        # Set up logging
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)
        # Register signal handling
        signal.signal(signal.SIGINT, self._die)
        signal.signal(signal.SIGTERM, self._die)
        signal.signal(signal.SIGHUP, self.configure)

    def configure(self):
        """Try config files and if one is found, parse it."""
        for cfgfile in self.possible_config_files:
            if os.path.isfile(cfgfile):
                with open(cfgfile, 'r') as handle:
                    self.config = PARSE(handle.read())

    def _die(self, signal_number, frame):  # pylint: disable=W0613
        """Set flag for main thread to die"""
        self.logger.info('Notifying main thread to gracefully terminate.')
        self.dying = True

    def _drainstop_threads(self):
        """
        Inspect each thread.
        If it's one we care about, attempt to call stop.
        """
        for thread in threading.enumerate():
            if isinstance(thread, tuple(self.monitored_thread_types)):
                if callable(getattr(thread, 'stop', None)):
                    thread.stop()
                    thread.join()
                else:
                    self.logger.error(
                        "Thread %s is missing stop().  Skipping.",
                        thread.name
                    )

    def _tend_the_threads(self):
        """Generic thread tender."""
        for thread_type in self.monitored_thread_types:
            if thread_type not in [type(t) for t in threading.enumerate()]:
                thread_type().start()
            for thread in threading.enumerate():
                if thread_type == type(thread):
                    if not thread.is_alive():
                        thread_type().start()

    def run(self):
        """The main loop."""
        self.configure()
        while True:
            if self.dying:
                self._drainstop_threads()
                break
            else:
                self._tend_the_threads()
            sleep(1)
        self.logger.info('Main thread complete.')


if __name__ == '__main__':
    APP = Main()
    APP.run()
