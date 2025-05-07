import json


class Config:
    def __init__(self, file_path="CONFIG.json"):
        self.VALID_BAR_PERIODS = {
            "1 min",
            "2 mins",
            "3 mins",
            "5 mins",
            "10 mins",
            "15 mins",
            "20 mins",
            "30 mins",
            "1 hour",
            "2 hours",
            "3 hours",
            "4 hours",
            "8 hours",
            "1 day",
        }

        self.BAR_PERIOD_TO_SECONDS = {
            "1 min": 60,
            "2 mins": 120,
            "3 mins": 180,
            "5 mins": 300,
            "10 mins": 600,
            "15 mins": 900,
            "20 mins": 1200,
            "30 mins": 1800,
            "1 hour": 3600,
            "2 hours": 7200,
            "3 hours": 10800,
            "4 hours": 14400,
            "8 hours": 28800,
            "1 day": 86400,
        }

        self.RUN_ON_REAL = None
        self.FAST_EMA_PARAMETER = None
        self.SLOW_EMA_PARAMETER = None
        self.TRAILING_STOP_PERCENTAGE = None
        self.REBUY_TRIGGER = None
        self.CLOSE_POSITION_AT_EOD = None
        self.BAR_PERIOD = None
        self.START_TRADING_TIME = None
        self.END_TRADING_TIME = None
        self.DOLLARS_PER_TRADE = None

        self.file_path = file_path
        self.config_data = self.read_config_file()
        self.mapping = {
            "Execute on Real Account": "RUN_ON_REAL",
            "Fast EMA Parameter": "FAST_EMA_PARAMETER",
            "Slow EMA Parameter": "SLOW_EMA_PARAMETER",
            "Trailing Stop %": "TRAILING_STOP_PERCENTAGE",
            "Rebuy Trigger": "REBUY_TRIGGER",
            "Close position at end of day": "CLOSE_POSITION_AT_EOD",
            "Bar Period": "BAR_PERIOD",
            "Start trading time (NY)": "START_TRADING_TIME",
            "End trading time (NY)": "END_TRADING_TIME",
            "Dollars per trade": "DOLLARS_PER_TRADE",
        }

        self.apply_config()

    def read_config_file(self):
        try:
            with open(self.file_path, "r") as file:
                return json.load(file)
        except:
            print("SEVERE WARNING: Unable to find the CONFIG.json file")
            exit()

    def apply_config(self):
        for human_key, var_name in self.mapping.items():
            value = self.config_data.get(human_key)
            if value is None:
                print(f"SEVERE WARNING: Issue with: {human_key} - attribute.")
                print(
                    "Execution halted due to unexpected attributes in JSON. "
                    "Double check the CONFIG.json attributes, or restore it using the backup"
                )
                exit()

            # Validazione per BAR_PERIOD
            if var_name == "BAR_PERIOD" and value not in self.VALID_BAR_PERIODS:
                print(f"SEVERE WARNING: Invalid value for 'Bar Period': {value}")
                print(f"Allowed values: {', '.join(self.VALID_BAR_PERIODS)}")
                exit()

            setattr(self, var_name, value)

    def calculate_time_amount(self):
        """Calcola il time_amount per ottenere 20 * SLOW_EMA_PARAMETER barre"""
        if self.BAR_PERIOD not in self.BAR_PERIOD_TO_SECONDS:
            print(f"SEVERE WARNING: Unsupported bar period: {self.BAR_PERIOD}")
            exit()

        bar_duration = self.BAR_PERIOD_TO_SECONDS[self.BAR_PERIOD]
        total_seconds = 20 * self.SLOW_EMA_PARAMETER * bar_duration

        if total_seconds > 86400:
            return f"{1 + (total_seconds // 86400)} D"
        else:
            return f"{total_seconds} S"
