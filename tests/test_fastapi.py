import io
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from zulip_write_only_proxy import models, services

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def test_send_message(fastapi_client: "TestClient", zulip_client):
    zulip_response = {"id": 42, "msg": "", "result": "success"}
    zulip_client.send_message = MagicMock(return_value=zulip_response)

    response = fastapi_client.post(
        "/send_message",
        params={"topic": "Test Topic"},
        data={"content": "Test Content"},
    )

    assert response.status_code == 200
    assert response.json() == zulip_response

    # Check that the zulip client was called with the expected arguments
    zulip_request = {
        "type": "stream",
        "to": "Test Stream 1",
        "topic": "Test Topic",
        "content": "Test Content",
    }
    zulip_client.send_message.assert_called_once_with(zulip_request)


def test_send_message_unauthorised(fastapi_client):
    response = fastapi_client.post(
        "/send_message",
        headers={"X-API-key": "invalid_key"},
        params={"topic": "Test Topic"},
        data={"content": "Test Content"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorised"}


def test_send_message_with_image(fastapi_client, zulip_client):
    zulip_response_msg = {"id": 42, "msg": "", "result": "success"}
    zulip_response_file = {
        "msg": "",
        "result": "success",
        "uri": "/user_uploads/1/4e/m2A3MSqFnWRLUf9SaPzQ0Up_/zulip.txt",
    }

    zulip_client.send_message = MagicMock(return_value=zulip_response_msg)
    zulip_client.upload_file = MagicMock(return_value=zulip_response_file)

    image = io.BytesIO(b"test image data")
    response = fastapi_client.post(
        "/send_message",
        params={"topic": "Test Topic"},
        files={"image": ("test.jpg", image)},
        data={"content": "Test Content"},
    )

    assert response.status_code == 200
    assert response.json() == zulip_response_msg

    # Check that the zulip client was called with the expected arguments
    zulip_request_msg = {
        "type": "stream",
        "to": "Test Stream 1",
        "topic": "Test Topic",
        "content": f"Test Content\n[]({zulip_response_file['uri']})",
    }
    zulip_client.send_message.assert_called_once_with(zulip_request_msg)

    # Call is made with spooled temp file object
    zulip_client.upload_file.assert_called_once()
    uploaded_image = zulip_client.upload_file.call_args.args[0]
    assert uploaded_image.name == "test.jpg"


def test_update_message_move_topic(fastapi_client: "TestClient", zulip_client):
    zulip_response = {"msg": "", "result": "success"}
    zulip_client.update_message = MagicMock(return_value=zulip_response)

    response = fastapi_client.patch(
        "/update_message",
        params={"message_id": 42, "propagate_mode": "change_one", "topic": "New Topic"},
    )

    assert response.status_code == 200
    assert response.json() == zulip_response

    # Check that the zulip client was called with the expected arguments
    zulip_request = {
        "message_id": 42,
        "propagate_mode": "change_one",
        "topic": "New Topic",
    }
    zulip_client.update_message.assert_called_once_with(zulip_request)


def test_update_message_content(fastapi_client: "TestClient", zulip_client):
    zulip_response = {"msg": "", "result": "success"}
    zulip_client.update_message = MagicMock(return_value=zulip_response)

    response = fastapi_client.patch(
        "/update_message",
        params={"message_id": 42, "propagate_mode": "change_one"},
        headers={"Content-Type": "text/plain"},
        content="Test Content",
    )

    assert response.status_code == 200
    assert response.json() == zulip_response

    # Check that the zulip client was called with the expected arguments
    zulip_request = {
        "message_id": 42,
        "propagate_mode": "change_one",
        "content": "Test Content",
    }
    zulip_client.update_message.assert_called_once_with(zulip_request)


def test_update_message_missing_args(fastapi_client: "TestClient", zulip_client):
    response = fastapi_client.patch(
        "/update_message",
        params={"message_id": 42, "propagate_mode": "change_one"},
        headers={"Content-Type": "text/plain"},
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": (
            "Either content (update message text) or topic (rename message topic) must "
            "be provided"
        )
    }


def test_upload_file(fastapi_client, zulip_client):
    zulip_response_file = {
        "msg": "",
        "result": "success",
        "uri": "/user_uploads/1/4e/m2A3MSqFnWRLUf9SaPzQ0Up_/zulip.txt",
    }
    zulip_client.upload_file = MagicMock(return_value=zulip_response_file)

    file = io.BytesIO(b"test file data")
    response = fastapi_client.post(
        "/upload_file",
        files={"file": ("test.jpg", file)},
    )

    assert response.status_code == 200
    assert response.json() == zulip_response_file

    # Call is made with spooled temp file object
    zulip_client.upload_file.assert_called_once()
    uploaded_file = zulip_client.upload_file.call_args.args[0]
    assert uploaded_file.name == "test.jpg"


def test_get_stream_topics(fastapi_client, zulip_client):
    zulip_response_id = {"msg": "", "result": "success", "stream_id": 15}
    zulip_response_topics = {
        "msg": "",
        "result": "success",
        "topics": [
            {"max_id": 26, "name": "Denmark3"},
            {"max_id": 23, "name": "Denmark1"},
            {"max_id": 6, "name": "Denmark2"},
        ],
    }
    zulip_client.get_stream_id = MagicMock(return_value=zulip_response_id)
    zulip_client.get_stream_topics = MagicMock(return_value=zulip_response_topics)

    response = fastapi_client.get("/get_stream_topics")

    assert response.status_code == 200
    assert response.json() == zulip_response_topics


def test_get_stream_topics_error(fastapi_client, zulip_client):
    zulip_response_id = {"result": "error"}
    zulip_client.get_stream_id = MagicMock(return_value=zulip_response_id)

    response = fastapi_client.get("/get_stream_topics")

    assert response.status_code == 200
    assert response.json() == {"result": "error"}


def test_create_client(fastapi_client, zulip_client):
    zulip_client.create_client = MagicMock(return_value={"result": "success"})

    response = fastapi_client.post(
        "/create_client",
        headers={"X-API-key": "admin1"},
        params={"proposal_no": 1234, "stream": "Test Stream"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "key": "**********",
        "proposal_no": 1234,
        "stream": "Test Stream",
    }


def test_create_client_error(fastapi_client):
    with patch(
        "zulip_write_only_proxy.services.create_client",
        MagicMock(side_effect=ValueError("Test Error")),
    ):
        # Call the API endpoint with invalid data
        response = fastapi_client.post(
            "/create_client",
            headers={"X-API-key": "admin1"},
            params={"proposal_no": 1234, "stream": "Test Stream"},
        )

        assert response.status_code == 400
        assert response.json() == {"detail": "Test Error"}

        # Check that the services module was called with the expected arguments
        services.create_client.assert_called_once_with(1234, "Test Stream")


@pytest.mark.parametrize(
    "client_type,kwargs",
    [(models.AdminClient, {}), (models.ScopedClient, {"proposal_no": 0})],
)
def test_get_me(client_type, kwargs, fastapi_client, zulip_client):
    client = client_type.create(**kwargs)

    with patch(
        "zulip_write_only_proxy.services.get_client",
        MagicMock(return_value=client),
    ):
        response = fastapi_client.get(
            "/me",
            headers={"X-API-key": client.key.get_secret_value()},
        )

        assert response.status_code == 200
