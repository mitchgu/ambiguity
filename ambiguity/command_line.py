"""Command line entry points for the package"""
import argparse
import logging
from pathlib import Path

import yaml

from ambiguity.account_manager import AccountManager
from ambiguity.scd import SimpleChromeDriver
from ambiguity.utils import Namespace

LOG = logging.getLogger(__name__)

for module in ['selenium', 'pykeepass']:
    module_logger = logging.getLogger(module)
    module_logger.setLevel(logging.WARNING)
logging.basicConfig(
    level=logging.INFO,
    format="[{levelname}] {message}",
    style="{")


def get_settings():
    """Returns a settings namespace after parsing command args"""
    parser = argparse.ArgumentParser(
        description='Pull statements for all accounts')
    parser.add_argument('settings_file', nargs='?', default="settings.yaml")
    args = parser.parse_args()
    settings_path = Path(args.settings_file).expanduser()
    try:
        settings = Namespace(**yaml.load(settings_path.read_text()))
    except FileNotFoundError:
        LOG.critical("Settings file could not be found at %s",
                     settings_path.absolute())
        import sys
        sys.exit()
    return settings


def pull():
    """Pulls statements with an AccountManager and a settings file"""
    am = AccountManager(get_settings())
    am.pull_all()


def open_scd():
    """Opens the SimpleChromeDriver and falls into the interpreter for playing
    around with things"""
    settings = get_settings()
    download_dir = Path(settings.chrome_download_dir).expanduser()
    profile_dir = Path(settings.chrome_profile_dir).expanduser()
    with SimpleChromeDriver(download_dir, profile_dir) as scd:
        scd.start()
        import code
        code.interact(local=dict(globals(), **locals()))
