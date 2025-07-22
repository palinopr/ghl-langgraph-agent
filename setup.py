from setuptools import setup, find_packages

# Read requirements from requirements.txt
with open("requirements.txt") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="ghl-langgraph-agent",
    version="3.1.1",
    description="GoHighLevel LangGraph Agent",
    packages=find_packages(),
    install_requires=requirements,
    python_requires=">=3.11",
    author="Your Name",
    author_email="your.email@example.com",
)