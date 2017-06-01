"""Classes to provide credentials for online accounts"""
import abc
import getpass
import logging
from pathlib import Path

from pykeepass import PyKeePass

LOG = logging.getLogger(__name__)


class CredentialProvider(metaclass=abc.ABCMeta):
    """Abstract base class for all credential providers"""

    @abc.abstractmethod
    def get_credential(self, name):
        """Get a (username, password) tuple for the given credential name"""
        pass

    @staticmethod
    def factory(provider_type, **kwargs):
        """Factory method that returns a credential provider given a type"""
        if provider_type == "keepass":
            return KeepassCP(**kwargs)
        elif provider_type == "stdin":
            return StdinCP()
        else:
            raise ValueError("Credential provider {} not supported".format(
                provider_type))


class KeepassCP(CredentialProvider):
    """Concrete credential provider for keepass databases"""

    def __init__(self, kdbx_file):
        self.kdbx_file = Path(kdbx_file).expanduser()

    @property
    def kdbx(self):
        """A lazy loaded property for loading the pykeepass database"""
        if not hasattr(self, "__lazy_kdbx"):
            for _ in range(3):
                kdbx_pass = getpass.getpass("Keepass password: ")
                try:
                    setattr(self, "__lazy_kdbx", PyKeePass(
                        str(self.kdbx_file.absolute()), password=kdbx_pass))
                    break
                except FileNotFoundError:
                    LOG.critical("Could not find keepass database at %s",
                                 self.kdbx_file.absolute())
                    import sys
                    sys.exit()
                except IOError:
                    print("Keepass unlock failed")
            else:
                print("Too many password attempts. Exiting...")
                import sys
                sys.exit()
        return getattr(self, "__lazy_kdbx")

    def get_credential(self, name):
        entry = self.kdbx.find_entries_by_title(name, first=True)
        if entry is None:
            raise ValueError("Could not find credential with name {}".format(
                name))
        return entry.username, entry.password


class StdinCP(CredentialProvider):
    """Concrete credential provider for typing credentials via stdin"""

    def get_credential(self, name):
        username = input("{} username: ".format(name))
        password = getpass.getpass("{} password: ".format(name))
        return username, password
