import io
from unittest.mock import MagicMock

from structlog.testing import capture_logs


def test_upload_file(a_scoped_client):
    a_scoped_client._client.upload_file = MagicMock(
        return_value={"uri": "/foo/bar.jpg"}
    )

    file = io.BytesIO(b"test file data")

    result = a_scoped_client.upload_file(file)

    a_scoped_client._client.upload_file.assert_called_once_with(file)

    assert result == {"uri": "/foo/bar.jpg"}


def test_get_stream_topics(a_scoped_client):
    a_scoped_client._client.get_stream_id = MagicMock(
        return_value={"result": "success", "stream_id": 123}
    )
    a_scoped_client._client.get_stream_topics = MagicMock(
        return_value=["Topic 1", "Topic 2"]
    )

    result = a_scoped_client.get_stream_topics()

    a_scoped_client._client.get_stream_id.assert_called_once_with("Test Stream")

    a_scoped_client._client.get_stream_topics.assert_called_once_with(123)

    assert result == ["Topic 1", "Topic 2"]


def test_get_stream_topics_log(a_scoped_client):
    response = {
        "code": "BAD_REQUEST",
        "msg": "Invalid stream name 'nonexistent'",
        "result": "error",
    }

    a_scoped_client._client.get_stream_id = MagicMock(return_value=response)

    with capture_logs() as caplog:
        a_scoped_client.get_stream_topics()

    assert len(caplog) == 1
    assert caplog[0]["stream"] == "Test Stream"
    assert caplog[0]["response"] == response
    assert caplog[0]["event"] == "Failed to get stream id"


def test_send_message(a_scoped_client):
    a_scoped_client._client.send_message = MagicMock(return_value={"result": "success"})

    result = a_scoped_client.send_message("Test Topic", "Test Content")

    a_scoped_client._client.send_message.assert_called_once_with({
        "type": "stream",
        "to": "Test Stream",
        "topic": "Test Topic",
        "content": "Test Content",
    })

    assert result == {"result": "success"}
