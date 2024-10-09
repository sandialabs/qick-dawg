from qickdawg.util import *
from qickdawg.nvpulsing import *
from qickdawg.fitfunctions import *

import os
import importlib
import json
# Now using QICK 0.2.160 as of 7/03/2023

dir = os.path.dirname(os.path.abspath(__file__))

with importlib.resources.open_text("qickdawg", "version.json") as file:
    __version__ = json.load(file)['version']
