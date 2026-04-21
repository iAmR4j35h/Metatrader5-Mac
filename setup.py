"""
Setup script for MetaTrader5 macOS compatibility package.

This package provides a macOS-compatible implementation of the MetaTrader5
Python API by using a socket-based IPC bridge to communicate with MT5
running on Windows (via Wine/CrossOver) or in a VM.
"""

from setuptools import setup, find_packages
import os

# Read the README file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="metatrader5-macos",
    version="5.0.5735",
    author="MetaQuotes Ltd. / macOS Port",
    author_email="",
    description="MetaTrader5 API for macOS via socket bridge",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/iAmR4j35h/Metatrader5-Mac",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial :: Investment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: MacOS",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires=">=3.7",
    install_requires=[
        "numpy>=1.7",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov",
            "black",
            "flake8",
        ],
    },
    package_data={
        "MetaTrader5": ["*.py"],
        "MQL5": ["*.mq5", "*.mqh"],
    },
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "mt5-bridge=MetaTrader5.bridge:main",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/iAmR4j35h/Metatrader5-Mac/issues",
        "Source": "https://github.com/iAmR4j35h/Metatrader5-Mac",
        "Documentation": "https://www.mql5.com/en/docs/integration/python_metatrader5",
    },
)
