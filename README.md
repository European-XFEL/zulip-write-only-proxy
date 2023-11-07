# Zulip Write Only Proxy

## Usage

### Client

Recommended clients are `requests` for synchronous code and `httpx` for asynchronous code. These examples are written for a server running locally at <http://localhost:8080> but the actual URL will depend on the deployment.

Using requests (synchronous):

```python
import requests

base_url = "http://localhost:8080"

response = requests.post(f"{base_url}/{endpoint}", data=data, ...)
```

Using httpx (async):

```python
import httpx

base_url = "http://localhost:8080"

async with httpx.AsyncClient() as client:
    response = await client.post(f"{base_url}/{endpoint}", ...)
```

Replace `endpoint` with the desired endpoint (e.g. `send_message`).

### Authentication

Authentication is done by including the token in the header, for example:

```python
headers = {
    "accept": "application/json",
    "X-API-key": "token",
    "Content-Type": "multipart/form-data"
}
```

This header should be included in all requests. You can create a client which always has the header with:

```python
import requests  # or httpx

client = requests.Session()
client.headers.update({"X-API-key": "token"})
```

### Endpoints

Full API documentation is available by going to the `/docs` page (e.g. <http://localhost:8080/docs>). These examples are just intended to show basic usage and may not represent the current state of the API, check the API docs for the latest information.

#### Sending a message with text

```python
response = client.post(
    f"{base_url}/send_message",
    params={"topic": "test-read-only-thing-2"}
    data={"content": "I recommend muting this topic."},
)
```

#### Sending a message with text and an image

`/send_message` supports sending a file with a message. An inline link to the file will be included at the end of the text message.

```python
response = client.post(
    f"{base_url}/send_message",
    params={"topic": "test-read-only-thing-2"}
    data={'content': f'Interesting plot!'},
    files={'image': open('./downloads/recursion.jpg', 'rb')},
)
```

#### Creating a Client

If you have an admin token you can create a new client for a proposal and stream. This will create a new token for the client and return it:

```python
response = client.post(
    f"{base_url}/create_client",
    params={"proposal_no": 1234, "stream": "proposal 1234 stream"},
)
```

Note that admin tokens can only create clients, they cannot post to a stream as they have no associated stream.

## Development

### Setup

For development you can either use docker or install the package locally via Poetry.

For docker:

```sh
# Build the image:
docker build . --tag zwop:dev

# Start the server, with the current directory mounted as a volume:
docker run -it --rm -v $(PWD):/app -p 8080:8080 zwop:dev

# Or use make, which does the same thing:
make dev-docker
```

For a direct install with Poetry:

```sh
# Install and activate
poetry install
poetry shell

# Start the server using poe, see next section for more details on poe tasks
poe serve
```

### Client Configuration

The configuration is very basic and is stored in a JSON file. The client token is used as a key and the value is a dictionary containing the proposal number and stream name.

```json
{
  "t425dYYQAVAT9AZiPx5fe0nrLzQSPpjZW-54EdxOUPQ": {
    "proposal_no": 2222,
    "stream": "proposal 2222 stream",
  }
}
```

Stream/topic can be edited manually in the JSON file or set at creation time.

### Tasks

This project uses `poe` as a task runner for various commands (see [Poe the Poet](https://github.com/nat-n/poethepoet)).

List available commands with `poe`:

```sh
$ poe

CONFIGURED TASKS
  serve
  test
  lint
  format
  ruff
  black
  mypy
  pyright
```

Run a task with `poe <task>`:

```sh
poe lint  # Run linters - only checks, no code changes

poe format  # Run formatters - changes files in place

poe test  # Run tests

poe serve  # Run the server
```

### Todo

Tentative list of things to do in the future:

- [ ] Query MyMdC for the stream name given a proposal number
- [ ] Query MyMdC for the list of topics and pass that on instead of trying to get them with the Zulip API
- [ ] Improve logging (structlog/loguru? sentry?)

## Deployment

Deployment is similar to development with `docker compose`, but instead a docker stack is used to allow for better scaling and update configuration.

There are two required environment variables, the port to run on (`PORT`), and the tag to use for the image (`TAG`). These should be set in an `.env` file:

```env
PORT=8089
TAG=0.1.0
```

To quickly bring the service up or down run `make up` or `make down`.

To update, bump up the tag run `make up` again. This will pull in the latest image and perform a rolling restart of the service, which will first start the new container, wait for a successful health check, and then stop the old container.

For development use there is an additional variable `IMAGE` which can be set to the name of a local image to use instead of pulling from the registry. This is useful for testing changes. If you recently used `make dev-docker` that would have build an image tagged `zwop:dev` which you could then use by setting `IMAGE=zwop:dev` in the `.env` file (note that this will not reflect code changes since the last image build).

NB: There is an outstanding issue with `docker stack deploy` where it [does not load `.env` files](https://github.com/moby/moby/issues/29133) in the same way that `docker compose up` does. This is solved by running `docker compose config` to generate a compose-compliant file (with env vars substituted), making a few changes via `sed`, and piping that to `docker stack deploy -`. Check the `Makefile` to see the exact command.
