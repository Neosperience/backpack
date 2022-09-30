''' This module contains code to standardize the configuration of Panorama applications via
deploy-time parameters. It also contains a CLI (command-line interface) that generates
configuration snippets for the metadata and descriptor json files of your Panorama project.
'''

from .tool import cli
from .config import ConfigBase
from .serde import ConfigSerDeBase, IntegerListSerDe
