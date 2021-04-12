import json
import sys
from unittest import mock

import docker
import pytest
from versionchooserutils.chooser import VersionChooser

if sys.version_info[:2] >= (3, 8):
    from unittest.mock import AsyncMock
else:
    from asyncmock import AsyncMock

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio

SAMPLE_JSON = """{
    "core": {
        "tag": "master",
        "image": "bluerobotics/companion-core",
        "enabled": true,
        "webui": false,
        "network": "host",
        "binds": {
            "/dev/": {
                "bind": "/dev/",
                "mode": "rw"
            },
            "/var/run/wpa_supplicant/wlan0": {
                "bind": "/var/run/wpa_supplicant/wlan0",
                "mode": "rw"
            },
            "/tmp/wpa_playground": {
                "bind": "/tmp/wpa_playground",
                "mode": "rw"
            }
        },
        "privileged": true
    }
}"""

SAMPLE_IMAGE = json.loads(
    """{
   "attrs":{
      "date":"2021-04-09T17:51:18.065721638Z"
   },
   "id":"856fdf5e66c9b3697c25015556e7895c9066febb1a8ac8657a4eb41f2fc95a57"
}"""
)


@pytest.mark.asyncio
async def test_get_version() -> None:
    """Tests if VersionChooser.get_version is reading SAMPLE_JSON properly

    Interacts with:
        - docker client (get images)
        - Settigns file
    """
    client_mock = mock.MagicMock()
    chooser = VersionChooser(client_mock)

    attrs = {
        "images.get.return_value.id": "856fdf5e66c9b3697c25015556e7895c9066febb1a8ac8657a4eb41f2fc95a57",
        "images.get.return_value.attrs.__getitem__.return_value": {
            "date": "2021-04-09T17:51:18.065721638Z"
        },
    }
    client_mock.configure_mock(**attrs)

    # Mock so it doesn't try to read a real file from the filesystem
    with mock.patch("builtins.open", mock.mock_open(read_data=SAMPLE_JSON)):

        response = await chooser.get_version()
        result = json.loads(response.text)
        assert result["image"] == "bluerobotics/companion-core"
        assert result["tag"] == "master"
        assert len(client_mock.mock_calls) > 0


version = {"tag": "master", "image": "bluerobotics/companion-core", "pull": False}


@pytest.mark.asyncio
@mock.patch("aiohttp.web.StreamResponse.write", new_callable=AsyncMock)
@mock.patch("aiohttp.web.StreamResponse.prepare")
async def test_set_version(prepare_mock: mock.MagicMock, write_mock: AsyncMock) -> None:
    client = mock.MagicMock()
    chooser = VersionChooser(client)
    with mock.patch("builtins.open", mock.mock_open(read_data=SAMPLE_JSON)):

        request_mock = AsyncMock()
        request_mock.json = AsyncMock(return_value=version)
        result = await chooser.set_version(request_mock)
        assert await write_mock.called_once_with(
            '{  "core": {\n    "tag": "master",\n    "image": "bluerobotics/companion-core",\n    "enabled": true,\n  '
            '  "webui": false,\n    "network": "host",\n    "binds": {\n      "/dev/": {\n        "bind": "/dev/",\n  '
            '      "mode": "rw"\n      },\n      "/var/run/wpa_supplicant/wlan0": {\n        "bind": "/var/run/wpa_sup'
            'plicant/wlan0",\n        "mode": "rw"\n      },\n      "/tmp/wpa_playground": {\n        "bind": "/tmp/wp'
            'a_playground",\n        "mode": "rw"\n      }\n    },\n    "privileged": true\n  }\n}'
        )
        assert result.status == 200
        assert len(write_mock.mock_calls) > 0
        assert len(prepare_mock.mock_calls) > 0


@pytest.mark.asyncio
@mock.patch("json.load", return_value={})
async def test_set_version_invalid_settings(json_mock: mock.MagicMock) -> None:
    client = mock.MagicMock()
    chooser = VersionChooser(client)
    with mock.patch("builtins.open", mock.mock_open(read_data="{}")):
        request_mock = AsyncMock()
        request_mock.json = AsyncMock(return_value=version)
        result = await chooser.set_version(request_mock)
        assert result.status == 500
        assert len(json_mock.mock_calls) > 0


image_list = [
    mock.MagicMock(
        attrs={"Created": "2021-04-09T17:51:18.065721638Z"},
        id="856fdf5e66c9b3697c25015556e7895c9066febb1a8ac8657a4eb41f2fc95a57",
        tags=["test1"],
    ),
    mock.MagicMock(
        attrs={"Created": "2021-04-09T17:51:18.065721638Z"},
        id="856fdf5e66c9b36remoteID856fdf5e66c9b36",
        tags=["test2"],
    ),
]


@pytest.mark.asyncio
# @mock.patch("docker.client.ImageCollection.list", return_value=image_list)
@mock.patch("aiohttp.client.ClientSession.get")
async def test_get_available_versions_dockerhub_unavailable(
    get_mock: mock.MagicMock,
) -> None:
    get_mock.configure_mock(status=500)
    client_mock = mock.MagicMock()
    attrs = {"images.list.return_value": image_list}
    client_mock.configure_mock(**attrs)
    chooser = VersionChooser(client_mock)
    result = await chooser.get_available_versions("companion-core", "bluerobotics")
    data = json.loads(result.text)
    print(data)
    assert "local" in data
    assert "remote" in data
    assert data["local"][0]["tag"] == "test1"
    assert data["local"][1]["tag"] == "test2"
    assert len(client_mock.mock_calls) > 0


@pytest.mark.asyncio

async def test_get_available_versions() -> None:
    client_mock = mock.MagicMock()
    attrs = {"images.list.return_value": image_list}
    client_mock.configure_mock(**attrs)

    chooser = VersionChooser(client_mock)
    result = await chooser.get_available_versions("companion-core", "bluerobotics")
    # do it again to trigger the cache
    result = await chooser.get_available_versions("companion-core", "bluerobotics")
    data = json.loads(result.text)
    assert "local" in data
    assert "remote" in data
    print(data)
    assert data["local"][0]["tag"] == "test1"
    assert data["local"][1]["tag"] == "test2"
    assert len(client_mock.mock_calls) > 0


@pytest.mark.asyncio
async def test_get_version_invalid_file() -> None:
    client = mock.MagicMock()
    with mock.patch("builtins.open", mock.mock_open(read_data="{}")):
        chooser = VersionChooser(client)
        response = await chooser.get_version()
        assert response.status == 500


@pytest.mark.asyncio
@mock.patch("json.load")
async def test_get_version_json_exception(json_mock: mock.MagicMock) -> None:
    client = mock.MagicMock()
    json_mock.side_effect = Exception()
    with mock.patch("builtins.open", mock.mock_open(read_data="")):
        chooser = VersionChooser(client)
        response = await chooser.get_version()
        assert response.status == 500
        assert len(json_mock.mock_calls) > 0


@pytest.mark.asyncio
@mock.patch("json.load")
async def test_set_version_json_exception(json_mock: mock.MagicMock) -> None:
    client = mock.MagicMock()
    json_mock.side_effect = Exception()
    chooser = VersionChooser(client)
    with mock.patch("builtins.open", mock.mock_open(read_data="{}")):
        request_mock = AsyncMock()
        request_mock.json = AsyncMock(return_value=version)
        result = await chooser.set_version(request_mock)
        assert result.status == 500
        assert len(json_mock.mock_calls) > 0


def test_main() -> None:
    # Just import main so some of it is tested
    # pylint: disable=unused-import
    # pylint: disable=import-outside-toplevel
    import main
