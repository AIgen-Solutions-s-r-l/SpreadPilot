import socket
import threading
import time
from Log import Log
import requests


class ConnectionMonitor:
    """
    A class to monitor the bot's internet connection status in a separate thread, handling disconnections and reconnections.

    Attributes:
    - stop_thread: Flag to control the monitoring thread's execution.
    - connection_is_active: Indicates the current state of the internet connection.
    - thread: The thread that runs the connection monitoring function.
    - forced_wait: Time in seconds to wait between checks.
    - disconnection_threshold: Number of consecutive failed checks needed to declare a disconnection.
    - disconnection_counter: Counts failed connection attempts.
    - logger: Logger instance for logging connection status.
    - test_disconnection: Flag to manually test disconnection handling.

    Methods:
    - isConnectedToInternet: Checks if the bot can reach an external server (e.g., Google) to confirm internet connectivity.
    - monitor_connection: Continuously checks for internet connectivity, updates connection status, and logs disconnections.
    - waitConnectionBack: Waits until the internet connection is consistently back before proceeding.
    - start: Starts the monitoring thread.
    - stop: Stops the monitoring thread and waits for it to finish.
    - connectionStatus: Returns the current connection status.
    - logDisconnectionStatus: Logs messages related to the connection status, optionally printing to the console.

    This class ensures the bot can handle internet disconnections gracefully, pausing operations during disconnection and resuming once connectivity is restored.
    """

    def __init__(self, logger: Log, forced_wait=1, disconnection_threshold=5, test_disconnection=False):
        self.stop_thread = False
        self.connection_is_active = False
        self.thread = threading.Thread(target=self.monitor_connection)
        self.thread.daemon = True
        self.forced_wait = forced_wait
        self.disconnection_threshold = disconnection_threshold
        self.disconnection_counter = -1
        self.logger = logger
        self.test_disconnection = test_disconnection

    def isConnectedToInternet(self):
        try:
            response = requests.head("http://www.google.com", timeout=2)
            if response.status_code == 200:
                if self.disconnection_counter != 0:
                    self.logDisconnectionStatus('Connection established. Setting disconnection counter to 0')
                    self.disconnection_counter = 0
                    self.connection_is_active = True
                return True
            else:
                self.disconnection_counter += 1
                self.logDisconnectionStatus(f'Disconnection counter:  {self.disconnection_counter}/{self.disconnection_threshold}')
                return False

        except (requests.ConnectionError, requests.ReadTimeout) as e:

            self.disconnection_counter += 1

            self.logDisconnectionStatus(f'Disconnection counter: {self.disconnection_counter}/{self.disconnection_threshold}')

            # Log different errors based on the exception

            if isinstance(e, requests.ReadTimeout):

                self.logDisconnectionStatus("Request timed out.")

            elif isinstance(e, ConnectionError):

                self.logDisconnectionStatus("Connection error.")

            return False

    def monitor_connection(self):
        while not self.stop_thread:

            if self.test_disconnection:
                if input("\nINPUT ANYTHING TO TEST DISCONNECTION\n"):
                    self.connection_is_active = False

            if self.isConnectedToInternet():
                pass
            else:
                if self.disconnection_counter >= self.disconnection_threshold:
                    self.logDisconnectionStatus(f'DISCONNECTION DETECTED. Counter: {self.disconnection_counter}/{self.disconnection_threshold}', print=True)
                    self.connection_is_active = False

            time.sleep(self.forced_wait)

    def waitConnectionBack(self):
        counter = 0

        while counter != 3:
            connection_result = self.isConnectedToInternet()
            if connection_result == 0:
                counter = 0
            else:
                counter += 1

        self.logDisconnectionStatus('Connection is ready.')

    def start(self):
        self.thread.start()

        self.logDisconnectionStatus(f'Thread started')

    def stop(self):
        self.stop_thread = True
        self.thread.join()
        self.logDisconnectionStatus(f'Thread stopped')

    def connectionStatus(self):
        return self.connection_is_active

    def logDisconnectionStatus(self, message, print=False):

        if not print:
            self.logger.debugAndLog(f'[CONN. MONITOR] {message}')
        else:
            self.logger.printAndLog(f'[CONN. MONITOR] {message}')
