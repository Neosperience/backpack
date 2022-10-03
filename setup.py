import os
import codecs
import os.path

from setuptools import setup, find_packages

name = "panorama-backpack"

with open("requirements.txt", "r") as f:
    requires = [x.strip() for x in f if x.strip()]

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

def read(rel_path):
    here = os.path.abspath(os.path.dirname(__file__))
    with codecs.open(os.path.join(here, rel_path), 'r') as fp:
        return fp.read()

def get_version(rel_path):
    for line in read(rel_path).splitlines():
        if line.startswith("__version__"):
            delim = '"' if '"' in line else "'"
            return line.split(delim)[1]
    else:
        raise RuntimeError("Unable to find version string.")

version=get_version("backpack/__init__.py")

setup(
    name=name,
    version=version,
    description="Tools for AWS Panorama development",
    python_requires=">=3.7",
    packages=find_packages(exclude=["tests.*", "tests"]),
    package_dir={"backpack": "backpack"},
    include_package_data=True,
    install_requires=requires,
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Janos Tolgyesi",
    author_email='janos.tolgyesi@neosperience.com',
    url="https://github.com/Neosperience/backpack",
    download_url="https://github.com/Neosperience/backpack/archive/refs/tags/v{}.tar.gz".format(version),
    keywords=["aws", "panorama", "video-analysis"],
    entry_points={},
    zip_safe=False,
    classifiers=[
        "Programming Language :: Python :: 3.7",
    ],
    extras_require={
        "opencv": ["opencv-headless"]
    },
    test_suite='tests'
)
