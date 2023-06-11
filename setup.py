from setuptools import setup, find_packages

setup(
  name="everything",
  author="Dan Rodriguez",
  author_email="hi+everything@dan.ws",
  version="0.0.1",
  description="",
  url="",
  classifiers=[
    "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3.9",
  ],
  packages=find_packages(),
  install_requires=[
    # Core library requirements
    "asyncio>=3.4",
    "colorama>=0.4",
    "pydantic>=1.8",

    # Required by ChattyAI example
    "transformers>=4.29",
    "torch>=2.0",

    # Required by WebApp example
    "Flask-SocketIO>=5.3",
    "eventlet>=0.33",

    # Required by DemoAgent example
    "openai>=0.27.8",
  ],
)
