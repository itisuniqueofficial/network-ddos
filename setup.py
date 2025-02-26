from setuptools import setup, find_packages

setup(
    name="network-ddos",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "aiohttp>=3.8.0",
        "faker>=13.0.0",
        "matplotlib>=3.5.0",
        "tqdm>=4.64.0"
    ],
    entry_points={
        "console_scripts": [
            "network-ddos = network_ddos.cli:main"
        ]
    },
    author="It Is Unique Official",
    author_email="contact@itisuniqueofficial.com",
    description="An advanced network testing tool for educational purposes by It Is Unique Official",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    license="MIT",
    url="https://github.com/itisuniqueofficial/network-ddos",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Education",
        "Topic :: Software Development :: Testing"
    ],
    python_requires=">=3.8",
)
