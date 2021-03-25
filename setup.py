"""setup.py for ambiguity package"""
from setuptools import setup, find_packages

setup(
    name="ambiguity",
    version="0.1.0",
    description="Personal finance accounting package",
    long_description=(
        "On the road from the City of Skepticism,"
        "I had to pass through the Valley of Ambiguity"),
    url="https://github.com/mitchgu/ambiguity",
    author="Mitchell Gu",
    author_email="me@mitchgu.com",
    license="MIT",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Natural Language :: English",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3 :: Only"
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Topic :: Office/Business :: Financial :: Accounting",
    ],
    keywords="personal finance accounting",
    packages=find_packages(exclude=['contrib', 'docs', 'tests*']),
    install_requires=[
        "pykeepass",
        "selenium==4.0.0a3",
        "pypdf2===1.26.0",
        "PyYAML==5.4",
    ],
    entry_points={
        "console_scripts": [
            "ambi-pull=ambiguity.command_line:pull",
            "ambi-scd=ambiguity.command_line:open_scd"
        ],
    }
)
