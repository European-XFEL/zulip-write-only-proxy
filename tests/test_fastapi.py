import io
from unittest.mock import MagicMock, patch

from zulip_write_only_proxy import services


def test_send_message(fastapi_client, zulip_client):
    zulip_response = {"id": 42, "msg": "", "result": "success"}
    zulip_client.send_message = MagicMock(return_value=zulip_response)

    response = fastapi_client.post(
        "/message",
        params={"topic": "Test Topic", "content": "Test Content"},
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
        "/message",
        headers={"X-API-key": "invalid_key"},
        params={"topic": "Test Topic", "content": "Test Content"},
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
        "/message",
        params={"topic": "Test Topic", "content": "Test Content"},
        files={"image": ("test.jpg", image)},
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


def test_upload_file(fastapi_client, zulip_client):
    zulip_response_file = {
        "msg": "",
        "result": "success",
        "uri": "/user_uploads/1/4e/m2A3MSqFnWRLUf9SaPzQ0Up_/zulip.txt",
    }
    zulip_client.upload_file = MagicMock(return_value=zulip_response_file)

    image = io.BytesIO(b"test image data")
    response = fastapi_client.post(
        "/upload_file",
        files={"image": ("test.jpg", image)},
    )

    assert response.status_code == 200
    assert response.json() == zulip_response_file

    # Call is made with spooled temp file object
    zulip_client.upload_file.assert_called_once()
    uploaded_image = zulip_client.upload_file.call_args.args[0]
    assert uploaded_image.name == "test.jpg"


def test_get_topics(fastapi_client, zulip_client):
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

    response = fastapi_client.get("/get_topics")

    assert response.status_code == 200
    assert response.json() == zulip_response_topics


def test_get_topics_error(fastapi_client, zulip_client):
    zulip_response_id = {"result": "error"}
    zulip_client.get_stream_id = MagicMock(return_value=zulip_response_id)

    response = fastapi_client.get("/get_topics")

    assert response.status_code == 400
    assert response.json() == {
        "detail": (
            "Failed to get stream id for Test Stream 1. Is bot added to stream?\n"
            f"Response was {zulip_response_id}"
        )
    }


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
