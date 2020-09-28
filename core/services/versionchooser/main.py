#!/usr/bin/env python3
from typing import Any

import connexion
import docker
from aiohttp import web
from versionchooserutils.chooser import STATIC_FOLDER, VersionChooser

versionChooser = VersionChooser(docker.client.from_env())


async def index(_request: web.Request) -> Any:
    return await versionChooser.index(_request)


async def get_version() -> Any:
    return await versionChooser.get_version()


def is_valid_version(_image: str, _version: str) -> bool:
    return bool(versionChooser.is_valid_version(_image, _version))


async def apply_version(request: web.Request, image: str, tag: str, pull: bool) -> Any:
    return await versionChooser.apply_version(request, image, tag, pull)


async def set_version(request: web.Request) -> Any:
    return await versionChooser.set_version(request)


async def get_available_versions(name: str, repository: str) -> Any:
    return await versionChooser.get_available_versions(name, repository)


if __name__ == "__main__":
    app = connexion.AioHttpApp(__name__, specification_dir="openapi/")
    app.add_api(
        "versionchooser.yaml", arguments={"title": "Companion Version Chooser"}, pass_context_arg_name="request"
    )
    app.app.router.add_static("/static/", path=str(STATIC_FOLDER))
    app.app.router.add_route("GET", "/", index)
    app.run(port=8081)
