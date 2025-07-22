"""
Setup configuration for GHL LangGraph Agent
"""
from setuptools import setup, find_packages
import os

# Read requirements from requirements.txt
def read_requirements():
    """Read requirements from requirements.txt file"""
    with open("requirements.txt", "r") as f:
        requirements = []
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if line and not line.startswith("#"):
                requirements.append(line)
        return requirements

# Read README for long description
def read_readme():
    """Read README.md for long description"""
    if os.path.exists("README.md"):
        with open("README.md", "r", encoding="utf-8") as f:
            return f.read()
    return "GHL LangGraph Agent - Multi-agent system for lead qualification and appointment setting"

setup(
    name="ghl-langgraph-agent",
    version="1.0.0",
    description="Multi-agent system for GHL lead qualification using LangGraph",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="Main Outlet Media",
    author_email="support@mainoutletmedia.com",
    url="https://github.com/jaimeortiz/open-agent-platform",
    packages=find_packages(include=["app", "app.*", "src", "src.*"]),
    include_package_data=True,
    python_requires=">=3.11",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=8.0.0",
            "pytest-asyncio>=0.23.0",
            "pytest-cov>=4.1.0",
            "ruff>=0.2.0",
            "mypy>=1.8.0",
            "ipdb>=0.13.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "ghl-agent=app.app:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Communications :: Chat",
        "Framework :: AsyncIO",
    ],
    keywords="langgraph ghl agent multi-agent lead-qualification appointment-setting",
)