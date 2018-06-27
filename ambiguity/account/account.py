"""Abstract base class for an ambiguity account"""

import abc
from collections import defaultdict
import datetime
import logging
import re

from ambiguity import StatementDate
from ambiguity import account

LOG = logging.getLogger(__name__)


class Account(metaclass=abc.ABCMeta):
    """Abstract base class for all accounts to inherit from"""

    # pylint: disable=too-many-instance-attributes
    PULL_FMTS = set()

    # pylint: disable=too-many-arguments
    def __init__(self, name, open_date, lib_dir, statement_day=1, active=True,
                 cred_name=None, ignore=None):
        self.name = name
        self.cred_name = name if cred_name is None else cred_name
        self.open_date = open_date
        self.statement_day = statement_day
        self.lib_dir = lib_dir
        self.active = active
        self.build_library()
        self.ignore = defaultdict(set)
        if ignore:
            for iso_date, fmts in ignore.items():
                sd = StatementDate.from_iso(iso_date)
                if fmts is None:
                    self.ignore[sd] = self.PULL_FMTS.copy()
                else:
                    self.ignore[sd] = set(fmts)
        LOG.info("Loaded account %s, %d statements found", name,
                 len(self.library))

    def build_library(self):
        """Scan the library folder and add matching files to library"""
        self.library = defaultdict(set)
        self.lib_dir.mkdir(parents=True, exist_ok=True)
        file_name_re = re.compile(self.name + r"_([0-9]{4})_([0-9]{2})\.(\w+)")
        for fmt_dir in self.lib_dir.iterdir():
            if not fmt_dir.is_dir():
                continue
            for file in fmt_dir.iterdir():
                match = file_name_re.match(file.name)
                if match and match.group(3) == fmt_dir.name:
                    sd = StatementDate(match.group(1), match.group(2))
                    self.library[sd].add(fmt_dir.name)

    def file_statement(self, src_path, sd, fmt):
        """File a statement into the library"""
        fname = "{}_{}_{}.{}".format(
            self.name, sd.year, str(sd.month).zfill(2), fmt)
        (self.lib_dir / fmt).mkdir(exist_ok=True)
        dest_path = self.lib_dir / fmt / fname
        src_path.rename(dest_path)
        self.library[sd].add(fmt)

    def has_statement(self, sd, fmt):
        """Return whether a statement exists in the library"""
        return fmt in self.library[sd]

    def gen_statement_dates(self):
        """Generate all statement dates from account opening to now"""
        start_sd = StatementDate.from_datetime(self.open_date)
        end_sd = StatementDate.from_datetime(datetime.date.today())
        extra_start_month = self.open_date.day < self.statement_day
        extra_end_month = datetime.date.today().day > self.statement_day
        for ym in range(start_sd.ym + 1 - int(extra_start_month),
                        end_sd.ym + int(extra_end_month)):
            cur_sd = StatementDate.from_ym(ym)
            yield cur_sd

    @property
    def missing_statements(self):
        """Return all missing statements in the library, excluding ignores"""
        if not self.active:
            return dict()
        missing_statements = dict()
        for sd in self.gen_statement_dates():
            missing_fmts = self.PULL_FMTS - self.library[sd] - self.ignore[sd]
            if missing_fmts:
                missing_statements[sd] = missing_fmts
        return missing_statements

    def pull_missing(self, scd, credentials):
        """Pull all missing statements in the library"""
        ms = self.missing_statements
        if ms:
            LOG.info("%s: Missing statements: %s", self.name, ms)
        else:
            LOG.info("%s: No missing statements", self.name)
        self.pull(scd, credentials, ms, False)

    def pull_current(self, scd, credentials):
        """Pull current transactions into the library"""
        self.pull(scd, credentials, dict(), True)

    def pull(self, scd, cp, statements, pull_current=False):
        """Template method for pulling a list of statements into the library"""
        if not self.active:
            return
        if not statements and not pull_current:
            return
        credentials = cp.get_credential(self.cred_name)
        LOG.info("%s: Pulling statements", self.name)
        scd.start()
        scd.reset()
        self.do_pull(scd, credentials, statements, pull_current)

    @abc.abstractmethod
    def do_pull(self, scd, credentials, statements, pull_current=False):
        """Abstract method to pull a list of statements to be implemented
        by the concrete classes"""
        pass

    def log_failed_pull(self, sd, fmt):
        """Log a statement that could not be pulled"""
        LOG.warning("%s %s: Could not pull a %s statement", self.name, sd, fmt)

    def log_successful_pull(self, sd, fmt):
        """Log a successfully pulled statement"""
        LOG.info("%s %s: Pulled %s statement", self.name, sd, fmt)

    @staticmethod
    def factory(acct_type, **kwargs):
        """Factory method to return a concrete Account given a type"""
        if acct_type == "MITFCU":
            return account.MITFCU(**kwargs)
        elif acct_type == "MITFCU_Visa":
            return account.MITFCUVisa(**kwargs)
        elif acct_type == "BoA":
            return account.BoA(**kwargs)
        elif acct_type == "BoAVisa":
            return account.BoAVisa(**kwargs)
        elif acct_type == "USBankVisa":
            return account.USBankVisa(**kwargs)
        else:
            raise ValueError("Account type %s not supported", acct_type)
