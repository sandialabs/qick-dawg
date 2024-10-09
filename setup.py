import setuptools
import json


with open("./src/qickdawg/version.json") as file:
    __version__ = json.load(file)['version']

setuptools.setup(
    name='qickdawg',
    version=__version__)
