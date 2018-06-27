"""Helper class to represent a statement closing date"""
from functools import total_ordering
import datetime

@total_ordering
class StatementDate(object):
    """Represents a year-month pair for a statement. Hashable and comparable"""

    def __init__(self, year, month):
        self.year = int(year)
        self.month = int(month)

    @classmethod
    def from_iso(cls, iso):
        """Return a class instance from an ISO formatted string"""
        split = iso.split("-")
        return cls(split[0], split[1])

    @classmethod
    def from_datetime(cls, dt):
        """Return a class instance from a datetime instance"""
        return cls(dt.year, dt.month)

    @classmethod
    def from_ym(cls, ym):
        """Return a class instance from a year month representation"""
        return cls(ym // 12, ym % 12 + 1)

    @property
    def ym(self):
        """The year month representation of the instance"""
        return self.year * 12 + (self.month - 1)

    def to_datetime(self, day):
        return datetime.datetime(self.year, self.month, day)

    def __repr__(self):
        return "{}-{}".format(self.year, str(self.month).zfill(2))

    def __eq__(self, other):
        return self.ym == other.ym

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        return self.ym < other.ym

    def __hash__(self):
        return self.ym
