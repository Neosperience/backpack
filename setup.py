from glob import glob
import os

from setuptools import setup

name = "panorama-backpack"
version = "0.1.1"

# get the dependencies and installs
with open("requirements.txt", "r") as f:
    requires = [x.strip() for x in f if x.strip()]

setup(
    name=name,
    version=version,
    description="Tools for AWS Panorama development",
    python_requires=">=3.7",
    packages=["backpack"],
    package_dir={"backpack": "backpack"},
    py_modules=[os.path.splitext(os.path.basename(path))[0] for path in glob("src/*.py")],
    include_package_data=True,
    install_requires=requires,
    author="Janos Tolgyesi",
    author_email='janos.tolgyesi@neosperience.com',
    url="https://github.com/Neosperience/backpack",
    download_url="https://github.com/Neosperience/backpack/archive/refs/tags/v{}.tar.gz".format(version),
    keywords=["aws", "panorama", "video-analysis"],
    entry_points={},
    zip_safe=False,
    classifiers=[
        "Programming Language :: Python :: 3.8",
    ],
    extras_require={
    },
)
