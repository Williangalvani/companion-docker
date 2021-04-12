import json
import pathlib
from typing import Dict, List

import appdirs
import docker
from aiohttp import web
from versionchooserutils.dockerhub import TagFetcher

DOCKER_CONFIG_PATH = pathlib.Path(appdirs.user_config_dir("bootstrap"), "startup.json")

current_folder = pathlib.Path(__file__).parent.parent.absolute()
STATIC_FOLDER = pathlib.Path.joinpath(current_folder, "static")


class VersionChooser:
    def __init__(self, client: docker.DockerClient):
        self.client = client

    async def index(self, _request: web.Request) -> web.FileResponse:
        return web.FileResponse(str(STATIC_FOLDER) + "/index.html", headers={"cache-control": "no-cache"})

    async def get_version(self) -> web.Response:
        with open(DOCKER_CONFIG_PATH) as startup_file:
            try:
                core = json.load(startup_file)["core"]
                tag = core["tag"]
                image_name = core["image"]
                full_name = f"{image_name}:{tag}"
                image = self.client.images.get(full_name)
                print(image)
                output = {
                    "image": image_name,
                    "tag": tag,
                    "date": image.attrs["Created"],
                    "id": image.id.replace("sha256:", ""),
                }
                print(output)
                return web.json_response(output)
            except KeyError as e:
                return web.Response(status=500, text=f"Invalid version file: {e}")
            except Exception as error:
                return web.Response(status=500, text=f"Error: {type(error)}: {error}")

    @staticmethod
    def is_valid_version(_image: str, _version: str) -> bool:
        return True

    async def apply_version(self, request: web.Request, image: str, tag: str, pull: bool) -> web.StreamResponse:
        """Applies a new version.

        Sets the version in startup.json, launches bootstrap, and kills companion_core

        Args:
            request (web.Request): http request from aiohttp
            image (str): name of the image, such as bluerobotics/companion-core
            tag (str): image tag
            pull (bool): pull a new image from dockerhub (this will overwrite local changes)

        Returns:
            web.StreamResponse: Streams the 'docker pull' output
        """
        response = web.StreamResponse()
        response.headers["Content-Type"] = "application/x-www-form-urlencoded"
        await response.prepare(request)

        if pull:
            low_level_api = docker.APIClient(base_url="unix://var/run/docker.sock")
            for line in low_level_api.pull(f"{image}:{tag}", stream=True, decode=True):
                await response.write(f"{line}\n\n".replace("'", '"').encode("utf-8"))
            await response.write_eof()

        print("Starting bootstrap...")
        bootstrap = self.client.containers.get("companion-bootstrap")
        bootstrap.start()

        print("Stopping core...")
        core = self.client.containers.get("companion-core")
        core.kill()
        return response

    async def set_version(self, request: web.Request) -> web.StreamResponse:
        data = await request.json()
        tag = data["tag"]
        image = data["image"]
        pull = data["pull"]
        if not self.is_valid_version(image, tag):
            return web.Response(status=400, text="Invalid version")

        with open(DOCKER_CONFIG_PATH, "r+") as startup_file:
            try:
                data = json.load(startup_file)
                data["core"]["image"] = image
                data["core"]["tag"] = tag
                startup_file.seek(0)
                startup_file.write(json.dumps(data, indent=2))

                startup_file.truncate()
                return await self.apply_version(request, image, tag, pull)
            except KeyError:
                return web.Response(status=500, text="Invalid version file")
            except Exception as error:
                print(f"Error: {type(error)}: {error}")
                return web.Response(status=500, text=f"Error: {type(error)}: {error}")

    async def get_available_versions(self, name: str, repository: str) -> web.Response:
        output: Dict[str, List[Dict[str, str]]] = {"local": [], "remote": []}
        image_name = f"{repository}/{name}"
        for image in self.client.images.list(image_name):
            for tag in image.tags:
                output["local"].append(
                    {
                        "image": image_name,
                        "tag": tag.split(":")[-1],
                        "date": image.attrs["Created"],
                        "id": image.id.replace("sha256:", ""),
                    }
                )
        online_tags = await TagFetcher().fetch_remote_tags(image_name)
        output["remote"].extend(online_tags)

        return web.json_response(output)
