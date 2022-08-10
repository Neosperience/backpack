from glob import glob
import os

from setuptools import setup, find_packages

name = "panorama-backpack"
version = "0.1.5"

# get the dependencies and installs
with open("requirements.txt", "r") as f:
    requires = [x.strip() for x in f if x.strip()]

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

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
    },
)
