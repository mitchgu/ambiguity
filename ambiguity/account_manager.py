"""Account manager"""
import logging
from pathlib import Path

from ambiguity.account import Account
from ambiguity.credential_providers import CredentialProvider
from ambiguity.scd import SimpleChromeDriver

LOG = logging.getLogger(__name__)


class AccountManager(object):  # pylint: disable=too-few-public-methods
    """An account manager to perform operations across multiple accounts in
    a single library. Takes settings in the form of a Namespace.
    """

    def __init__(self, settings):
        self.cp = CredentialProvider.factory(**settings.credential_provider)
        self.library_dir = Path(settings.library_dir).expanduser()
        self.download_dir = Path(settings.chrome_download_dir).expanduser()
        self.profile_dir = Path(settings.chrome_profile_dir).expanduser()
        self.accounts = []
        for acct_params in settings.accounts:
            lib_dir = self.library_dir / acct_params["name"]
            self.accounts.append(
                Account.factory(**acct_params, lib_dir=lib_dir))

    def pull_all(self):
        """Pulls all missing statements from each account"""
        with SimpleChromeDriver(self.download_dir, self.profile_dir) as scd:
            for acct in self.accounts:
                acct.pull_missing(scd, self.cp)
