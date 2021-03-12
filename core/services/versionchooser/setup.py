#!/usr/bin/env python3

import pathlib
import ssl
import urllib.request
from warnings import warn

from setuptools import setup

ssl._create_default_https_context = ssl._create_unverified_context


static_files = {
    "js/axios.min.js": "https://cdnjs.cloudflare.com/ajax/libs/axios/0.19.2/axios.min.js",
    "js/jsonpipe.js": "https://raw.githubusercontent.com/eBay/jsonpipe/master/jsonpipe.js",
    "js/polyfill.min.js": "https://polyfill.io/v3/polyfill.min.js?features=es2015,IntersectionObserver",
    "js/vue.js": "https://unpkg.com/vue@latest/dist/vue.js",
}

current_folder = pathlib.Path(__file__).parent.absolute()
static_folder = pathlib.Path.joinpath(current_folder, "static")

for filename, url in static_files.items():
    path = pathlib.Path.joinpath(static_folder, filename)
    print(filename, path, path.parent)
    path.parent.mkdir(exist_ok=True)
    try:
        urllib.request.urlretrieve(url, path)
    except Exception as error:
        warn(f"unable to open url {url}, error {error}")

setup(
    name="versionchooser_service",
    version="0.1.0",
    description="Blue Robotics Ardusub Companion Version Chooser",
    license="MIT",
    install_requires=[
        "connexion[swagger-ui, aiohttp]",
        "docker",
        "aiohttp==3.6.2",
        "appdirs",
        "pytest-asyncio",
        "asyncmock",
        "werkzeug",
        "attr",
        "yaml",
    ],
)
