import sys
import time

from datetime import datetime, timedelta
import pytz
from dateutil import tz


def end_operations():
    input("Press Enter to continue...")
    sys.exit()


class nyTimeTools:

    @staticmethod
    def createNyDatetime(string, add_day=False):
        # Format: 'HH:MM:SS'. Set it to today
        if not add_day:
            day = nyTimeTools.currentTimeInNy().date()
        else:
            day = (nyTimeTools.currentTimeInNy() + timedelta(days=1)).date()

        nydatetime = datetime.combine(day, datetime.strptime(string, "%H:%M:%S").time())
        ny_timezone = pytz.timezone("America/New_York")
        nydatetime = ny_timezone.localize(nydatetime)
        return nydatetime

    @staticmethod
    def convertToNyTimezone(dt):
        local_tz = tz.tzlocal()
        dt = dt.replace(tzinfo=local_tz)

        ny_timezone = pytz.timezone("America/New_York")

        return dt.astimezone(ny_timezone)

    @staticmethod
    def convertNYTimeToLocal(ny_time):
        # Localize the input time to New York timezone if it's naive
        if ny_time.tzinfo is None:
            ny_timezone = pytz.timezone("America/New_York")
            ny_time = ny_timezone.localize(ny_time)

        # Convert to local timezone
        local_tz = tz.tzlocal()
        local_time = ny_time.astimezone(local_tz)

        return local_time

    @staticmethod
    def currentTimeInNy():
        dt = datetime.now()
        local_tz = tz.tzlocal()
        dt = dt.replace(tzinfo=local_tz)

        # Convert to New York timezone
        ny_timezone = pytz.timezone("America/New_York")
        return dt.astimezone(ny_timezone)

    @staticmethod
    def waitTillTime(target_time):
        wait_seconds = (target_time - nyTimeTools.currentTimeInNy()).total_seconds()
        time.sleep(wait_seconds)


class manageOptionChains:

    @staticmethod
    def remove_keys_within_range(dictionary, target, range_value):
        return {
            k: v
            for k, v in dictionary.items()
            if not (target - range_value <= k <= target + range_value)
        }

    @staticmethod
    def find_closest_key(dictionary, target, both_boundary=False):
        sorted_keys = sorted(dictionary.keys())
        if both_boundary:
            lower_key = None
            upper_key = None

            for key in sorted_keys:
                if key <= target:
                    lower_key = key
                elif key > target and upper_key is None:
                    upper_key = key
                    break

            # Handle edge cases
            if lower_key is None:  # target is smaller than all keys
                lower_key = sorted_keys[0]
            if upper_key is None:  # target is larger than all keys
                upper_key = sorted_keys[-1]

            return lower_key, upper_key
        else:
            # Return only the closest key
            return min(sorted_keys, key=lambda k: abs(k - target))
