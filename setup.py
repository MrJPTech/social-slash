#!/usr/bin/env python3
"""
Social Slash - Setup Configuration

Install with: pip install -e .
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="social-slash",
    version="0.1.0",
    author="PRSMTECH",
    author_email="dev@prsmtech.com",
    description="Social media automation slash commands for Claude Code",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/MrJPTech/social-slash",
    packages=find_packages(where="lib"),
    package_dir={"": "lib"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.10",
    install_requires=[
        "late-sdk>=1.2.17",
        "requests>=2.31.0",
        "httpx>=0.27.0",
        "python-dotenv>=1.0.0",
        "pydantic>=2.0.0",
    ],
    extras_require={
        "ai": [
            "anthropic>=0.40.0",
            "google-generativeai>=0.8.0",
        ],
        "browser": [
            "playwright>=1.48.0",
        ],
        "dev": [
            "pytest>=7.4.0",
            "black>=24.0.0",
            "mypy>=1.0.0",
        ],
        "all": [
            "anthropic>=0.40.0",
            "google-generativeai>=0.8.0",
            "playwright>=1.48.0",
            "pytest>=7.4.0",
            "black>=24.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "social-post=posting.poster:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["data/*.json"],
    },
)
