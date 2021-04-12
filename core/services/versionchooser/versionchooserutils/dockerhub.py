#!/usr/bin/env python3
"""
Responsible for interacting with dockerhub
adapted from https://github.com/al4/docker-registry-list
"""

import json
from typing import Dict, List, Optional
from warnings import warn

import aiohttp


class TagFetcher:
    """Fetches remote tags for a given image"""

    # Holds the information once it is fetched so we don't do it multiple times
    cache: Dict[str, List[Dict[str, str]]] = {}
    index_url: str = "https://index.docker.io"

    @staticmethod
    async def _get_token(auth_url: str, image_name: str) -> str:
        """[summary]
        Gets a token for dockerhub.com
        Args:
            auth_url: authentication url, default to https://auth.docker.io
            image_name: image name, for example "bluerobotics/core"

        Raises:
            Exception: Raised if unable to get the token

        Returns:
            The token
        """
        payload = {
            "service": "registry.docker.io",
            "scope": "repository:{image}:pull".format(image=image_name),
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(auth_url + "/token", params=payload) as resp:
                if resp.status != 200:
                    warn("Error status {}".format(resp.status))
                    raise Exception("Could not get auth token")
                return str((await resp.json())["token"])

    async def fetch_metadata(self, image: str, tag: str, header: Dict[str, str]) -> Dict[str, str]:
        """Fetchs metadata for a given tag. We are interested in id and creation date"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.index_url}/v2/{image}/manifests/{tag}", headers=header) as resp:
                if resp.status != 200:
                    warn("Error status {}".format(resp.status))
                    raise Exception("Failed getting tags from DockerHub!")
                data = await resp.text()
                meta = json.loads(json.loads(data)["history"][0]["v1Compatibility"])
                date = meta["created"]
                tag_id = meta["id"]
                return {"image": image, "tag": tag, "date": date, "id": tag_id}

    async def fetch_remote_tags(
        self,
        image_name: str,
        token: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """Fetches the tags available for an image in DockerHub

        Args:
            image_name (str): Image to fetch tags for, for example "bluerobotics/core"
            index_url (str, optional): [description]. Defaults to "https://index.docker.io".
            token (Optional[str], optional): Token to use. Gets a new one if None is supplied

        Returns:
            List[str]: A list of tags available on DockerHub
        """
        if image_name in self.cache:
            return self.cache[image_name]

        header = None
        try:
            if token is None:
                token = await self._get_token(auth_url="https://auth.docker.io", image_name=image_name)
            header = {"Authorization": "Bearer {}".format(token)}
        except Exception as error:
            print(type(error), error)
            return []

        async with aiohttp.ClientSession() as session:
            async with session.get("{}/v2/{}/tags/list".format(self.index_url, image_name), headers=header) as resp:
                if resp.status != 200:
                    warn("Error status {}".format(resp.status))
                    raise Exception("Failed getting tags from DockerHub!")
                data = await resp.json()

                if "tags" not in data:
                    return []
                tags = [await self.fetch_metadata(image_name, tag, header) for tag in list(data["tags"])]
                self.cache[image_name] = tags
                return tags
