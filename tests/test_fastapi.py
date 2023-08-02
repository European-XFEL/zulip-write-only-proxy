import io
from unittest.mock import MagicMock

from zulip_write_only_proxy import models, services


def test_send_message(fastapi_client, zulip_client):
    zulip_client.send_message = MagicMock(return_value={"result": "success"})

    response = fastapi_client.post(
        "/message",
        params={"topic": "Test Topic", "content": "Test Content"},
    )

    assert response.status_code == 200
    assert response.json() == {"result": "success"}

    # Check that the zulip client was called with the expected arguments
    zulip_request = {
        "type": "stream",
        "to": "Test Stream 1",
        "topic": "Test Topic",
        "content": "Test Content",
    }
    zulip_client.send_message.assert_called_once_with(zulip_request)


def test_send_message_invalid_key(fastapi_client):
    # Call the API endpoint with an invalid key
    response = fastapi_client.post(
        "/message",
        headers={"X-API-key": "invalid_key"},
        params={"topic": "Test Topic", "content": "Test Content"},
    )

    # Check that the response has a 404 status code and the expected error message
    assert response.status_code == 404
    assert response.json() == {"detail": "Key not found"}


def test_send_message_with_image(fastapi_client):
    # Mock the services module
    services.send_message = MagicMock(return_value={"result": "success"})

    # Call the API endpoint with valid data and an image
    image = io.BytesIO(b"test image data")
    response = fastapi_client.post(
        "/message",
        headers={"X-API-key": "test_key"},
        params={"topic": "Test Topic", "content": "Test Content"},
        files={"image": ("test.jpg", image)},
    )

    # Check that the response has a 200 status code and the expected result
    assert response.status_code == 200
    assert response.json() == {"result": "success"}

    # Check that the services module was called with the expected arguments
    services.send_message.assert_called_once_with(
        models.ScopedClient.create("test_key"), "Test Topic", "Test Content", image
    )


def test_upload_image(fastapi_client):
    # Mock the services module
    services.upload_image = MagicMock(return_value={"uri": "/foo/bar.jpg"})

    # Call the API endpoint with valid data
    image = io.BytesIO(b"test image data")
    response = fastapi_client.post(
        "/upload_image",
        headers={"X-API-key": "test_key"},
        files={"image": ("test.jpg", image)},
    )

    # Check that the response has a 200 status code and the expected result
    assert response.status_code == 200
    assert response.json() == {"uri": "/foo/bar.jpg"}

    # Check that the services module was called with the expected arguments
    services.upload_image.assert_called_once_with(
        models.ScopedClient.create("test_key"), image
    )


def test_get_topics(fastapi_client):
    # Mock the services module
    services.list_topics = MagicMock(return_value=["Topic 1", "Topic 2"])

    # Call the API endpoint with valid data
    response = fastapi_client.get("/get_topics", headers={"X-API-key": "test_key"})

    # Check that the response has a 200 status code and the expected result
    assert response.status_code == 200
    assert response.json() == ["Topic 1", "Topic 2"]

    # Check that the services module was called with the expected arguments
    services.list_topics.assert_called_once_with(models.ScopedClient.create("test_key"))


def test_get_topics_error(fastapi_client):
    # Mock the services module to raise an error
    services.list_topics = MagicMock(side_effect=RuntimeError("Test Error"))

    # Call the API endpoint with valid data
    response = fastapi_client.get("/get_topics", headers={"X-API-key": "test_key"})

    # Check that the response has a 400 status code and the expected error message
    assert response.status_code == 400
    assert response.json() == {"detail": "Test Error"}

    # Check that the services module was called with the expected arguments
    services.list_topics.assert_called_once_with(models.ScopedClient.create("test_key"))


def test_create_client(fastapi_client):
    # Mock the services module
    services.create_client = MagicMock(return_value={"result": "success"})

    # Call the API endpoint with valid data
    response = fastapi_client.post(
        "/create_client",
        headers={"X-API-key": "admin_key"},
        params={"proposal_no": 1234, "stream": "Test Stream"},
    )

    # Check that the response has a 200 status code and the expected result
    assert response.status_code == 200
    assert response.json() == {"result": "success"}

    # Check that the services module was called with the expected arguments
    services.create_client.assert_called_once_with(1234, "Test Stream")


def test_create_client_error(fastapi_client):
    # Mock the services module to raise an error
    services.create_client = MagicMock(side_effect=ValueError("Test Error"))

    # Call the API endpoint with invalid data
    response = fastapi_client.post(
        "/create_client",
        headers={"X-API-key": "admin_key"},
        params={"proposal_no": 1234, "stream": "Test Stream"},
    )

    # Check that the response has a 400 status code and the expected error message
    assert response.status_code == 400
    assert response.json() == {"detail": "Test Error"}

    # Check that the services module was called with the expected arguments
    services.create_client.assert_called_once_with(1234, "Test Stream")
