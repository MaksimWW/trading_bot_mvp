
"""
Setup script for Trading Bot MVP
"""

from setuptools import setup, find_packages

setup(
    name="trading-bot-mvp",
    version="0.1.0",
    description="Automated trading bot for Russian stock market with Telegram interface",
    author="Trading Bot Team",
    packages=find_packages(),
    install_requires=[
        "tinkoff-investments",
        "python-telegram-bot",
        "pandas",
        "numpy",
        "requests",
        "sqlalchemy",
        "python-dotenv",
        "ta-lib",
        "matplotlib",
        "pytest",
    ],
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Insurance Industry",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)
