import os
from datetime import datetime


class Log:
    def __init__(self, debug):
        self.debug = debug

        # Create logs directory if it doesn't exist
        logs_path = os.path.join(os.getcwd(), 'Logs')
        if not os.path.exists(logs_path):
            os.makedirs(logs_path)
            print("Creating folder: Logs. Storing bot logs inside it.")
        else:
            print('Storing Logs inside Logs/...')

        # Create a new log.txt file with the current timestamp
        file_name = datetime.now().strftime("%d-%m %H_%M_%S") + '.txt'
        self.saving_path = os.path.join(logs_path, file_name)

        with open(self.saving_path, "w+") as file:
            pass

        self.printAndLog('Saving in path => ' + self.saving_path)

    def printAndLog(self, strg):
        timestamped_msg = datetime.now().strftime("%H:%M:%S") + ' || ' + strg
        print(timestamped_msg)
        self.appendNewLine(timestamped_msg)

    def debugAndLog(self, strg):
        timestamped_msg = datetime.now().strftime("%H:%M:%S") + ' || [DEBUG] ' + strg
        if self.debug:
            print(timestamped_msg)
        self.appendNewLine(timestamped_msg)

    def appendNewLine(self, string):
        with open(self.saving_path, "a+") as file_object:
            file_object.write(string + "\n")