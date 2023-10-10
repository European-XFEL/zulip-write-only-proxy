import io
from unittest.mock import MagicMock

import pytest

from zulip_write_only_proxy.models import AdminClient


def test_upload_file(scoped_client):
    scoped_client._client.upload_file = MagicMock(return_value={"uri": "/foo/bar.jpg"})

    file = io.BytesIO(b"test file data")

    result = scoped_client.upload_file(file)

    scoped_client._client.upload_file.assert_called_once_with(file)

    assert result == {"uri": "/foo/bar.jpg"}


def test_get_stream_topics(scoped_client):
    scoped_client._client.get_stream_id = MagicMock(
        return_value={"result": "success", "stream_id": 123}
    )
    scoped_client._client.get_stream_topics = MagicMock(
        return_value=["Topic 1", "Topic 2"]
    )

    result = scoped_client.get_stream_topics()

    scoped_client._client.get_stream_id.assert_called_once_with("Test Stream")

    scoped_client._client.get_stream_topics.assert_called_once_with(123)

    assert result == ["Topic 1", "Topic 2"]


def test_get_stream_topics_log(scoped_client, caplog: pytest.LogCaptureFixture):
    scoped_client._client.get_stream_id = MagicMock(
        return_value={
            "code": "BAD_REQUEST",
            "msg": "Invalid stream name 'nonexistent'",
            "result": "error",
        }
    )

    scoped_client.get_stream_topics()

    assert len(caplog.records) == 1
    assert caplog.records[0].message == (
        "failed to get stream id for Test Stream, zulip api response: "
        f"{scoped_client._client.get_stream_id.return_value}"
    )


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
