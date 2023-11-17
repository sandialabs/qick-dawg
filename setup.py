import os
from setuptools import setup, find_packages

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "qickdawg",
    version = "0.1.0",
    author = "Andrew Mounce, Emmeline Riendeau",
    author_email = "amounce@sandia.gov",
    description = ("Software for full quantum control of nitrogen-vacancy defects and other quantum defects in diamond through microwave and laser pulsing control."),
    license = "MIT",
    keywords = "quantum control diamond defect qubit",
    url = "",
    packages = find_packages(exclude=['qick', 'graphics', 'installation', 'jupyter_notebooks']),
    long_description = read('ReadMe.md'),
    long_description_content_type="text/markdown",
    install_requires=[
        #"ipykernel",
        "numpy",
        "matplotlib",
        "pyro4",
        "serpent",
        "tqdm",
        "scipy",
        "qick==0.2.160"
    ],
    extras_require={},
    classifiers = [
        "Development Status :: 2 - Pre-Alpha",
        "License :: MIT",
    ],
    python_requires='>=3.6',
)
