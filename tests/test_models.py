import io
from unittest.mock import MagicMock

import pytest

from zulip_write_only_proxy.models import AdminClient


def test_upload_image(scoped_client):
    scoped_client._client.upload_file = MagicMock(return_value={"uri": "/foo/bar.jpg"})

    image = io.BytesIO(b"test image data")

    result = scoped_client.upload_image(image)

    scoped_client._client.upload_file.assert_called_once_with(image)

    assert result == {"uri": "/foo/bar.jpg"}


def test_list_topics(scoped_client):
    scoped_client._client.get_stream_id = MagicMock(
        return_value={"result": "success", "stream_id": 123}
    )
    scoped_client._client.get_stream_topics = MagicMock(
        return_value=["Topic 1", "Topic 2"]
    )

    result = scoped_client.list_topics()

    scoped_client._client.get_stream_id.assert_called_once_with("Test Stream")

    scoped_client._client.get_stream_topics.assert_called_once_with(123)

    assert result == ["Topic 1", "Topic 2"]


def test_list_topics_raises(scoped_client):
    scoped_client._client.get_stream_id = MagicMock(return_value={"result": "failure"})

    with pytest.raises(RuntimeError):
        scoped_client.list_topics()


def test_send_message(scoped_client):
    scoped_client._client.send_message = MagicMock(return_value={"result": "success"})

    result = scoped_client.send_message("Test Topic", "Test Content")

    scoped_client._client.send_message.assert_called_once_with(
        {
            "type": "stream",
            "to": "Test Stream",
            "topic": "Test Topic",
            "content": "Test Content",
        }
    )

    assert result == {"result": "success"}


def test_admin_client_create():
    client = AdminClient.create()

    assert client.key is not None

    assert client.admin is True


def test_admin_client_init():
    result = AdminClient(key="", admin=True)  # type: ignore[assignment]

    assert result.admin

    with pytest.raises(ValueError):
        AdminClient(key="", admin=False)  # type: ignore[assignment]
