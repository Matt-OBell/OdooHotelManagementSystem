"""Collection of helper functions."""
import time
# from odoo.tools.misc import DEFAULT_SERVER_TIME_FORMAT


def decimal_to_time(number):
    """
    1. Take the decimal part of  number after the point and multiply it by 3600 i.e 60 * 60.
    2. Divide the answer from Step 1 by 60 and round it down
    """
    if number:
        hour, decimal = number.split('.')
        t = time.strptime(hour + ':' + decimal, '%H:%M')
        return t.tm_hour, t.tm_hour
    return False
