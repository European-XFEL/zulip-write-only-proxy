# Zulip Write Only Proxy

## Usage

### Client

Recommended clients are `requests` for synchronous code and `httpx` for asynchronous code. These examples are written for a server running locally at <http://localhost:8000> but the actual URL will depend on the deployment.

Using requests (synchronous):

```python
import requests

base_url = "http://localhost:8000"

response = requests.post(f"{base_url}/{endpoint}", data=data, ...)
```

Using httpx (async):

```python
import httpx

base_url = "http://localhost:8000"

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

Full API documentation is available by going to the `/docs` page (e.g. <http://localhost:8000/docs>). These examples are just intended to show basic usage and may not represent the current state of the API, check the API docs for the latest information.

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

### Local

`uv` is used as the package/project manager. The repository is set up as a uv workspace, with two packages: `zwop` (`packages/zwop`) and `zwop-tws` (`packages/token-writer`).

Useful commands for development:

```bash
uv sync  # installs entire workspace

bash ./scripts/generate-mtls.sh  # create mtls certs

uv run zwop  # start main zwop service

uv run zwop-tws  # start token writer service
```

You will need to create a `.env` file with the following:

```bash
# can be left blank - only required for web frontend
ZWOP_SESSION_SECRET=  # openssl rand -base64 32
ZWOP_AUTH__CLIENT_ID=
ZWOP_AUTH__CLIENT_SECRET=

# required for MyMdC queries
ZWOP_MYMDC__ID=
ZWOP_MYMDC__SECRET=
ZWOP_MYMDC__EMAIL=
```

The default configuration is set up for local development, so the two services will try and communicate over `localhost`.

### Compose

A compose stack is defined to start up a more 'realistic' development environment, which includes traefik in front of zwop.

After setting the required configurations in `.env` you can:

```bash
docker compose up --build

# or explicit build to inject 'correct' version no
docker compose build --build-arg APP_VERSION=(uvx --directory ./packages/zwop hatch version)
```

This will start:

- <http://localhost:8080/dashboard/> - Traefik dashboard
- <http://localhost:8000/zwop-dev/> - zwop
- <http://localhost:8000/zwop-dev/docs> - zwop api docs

Which allows for testing functionality in a similar environment to the deployment environment, e.g. path prefix behaviour.

### Debugging

When debugging it can be very useful, especially given the async nature of the API, to do so interactively. If using VSCode this can be done by creating a launch configuration for FastAPI. This will start the server and allow you to set breakpoints and step through the code.

Here is an example configuration, placed in `.vscode/launch.json`:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: FastAPI",
            "type": "python",
            "request": "launch",
            "module": "uvicorn",
            "args": [
                "zwop.main:app",
                "--port",
                "8000",
            ],
            "jinja": true,
            "justMyCode": false
        },
        {
            "name": "Python: FastAPI - Test Debug",
            "type": "python",
            "request": "launch",
            "module": "pytest",
            "jinja": true,
            "justMyCode": false
        }
    ]
}
```

This will add two configurations to the debug menu, one for running the server and one for running tests. The `justMyCode` option is set to `false` to allow for debugging/stepping into third party libraries.

See the [VSCode Debugging documentation](https://code.visualstudio.com/docs/editor/debugging) for more information.

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
  test
  lint
  format
```

Run a task with `poe <task>`:

```sh
poe lint  # Run linters - only checks, no code changes

poe format  # Run formatters - changes files in place

poe test  # Run tests
```

## Deployment and Maintenance

### ZWOP

Production deployments of ZWOP run on the DA dev server and use the container images built by the GitHub CI. When a new release is made, that image is tagged as `stable`, which is the image that will be used by the production compose (`compose.prod.yml`).

Useful commands are:

```bash
# production repo is in this directory
cd /srv/zwop/prod

# to update after a new release:
## update checkout
git pull
git checkout ${TAG}  # e.g. v0.4.1

## fetch newest image
docker compose -f compose.prod.yml pull

## (re)start the container
docker compose -f compose.prod.yml up -d

# troubleshooting:
## restart without update
docker compose -f compose.prod.yml restart

## view logs
docker compose -f compose.prod.yml logs
```

Note that the certificates in `./certs` should be in sync with those on the TWS host.

### ZWOP - Token Writer Service

TWS is a service running on Maxwell which ZWOP contacts to write tokens to GPFS.

Check the production configuration (`/srv/zwop/prod/.env`) to see where ZWOP expects to contact the TWS at (e.g. `https://max-exfl463.desy.de:8443/`). The following assumes you're on the node specified above as `xdana`.

The service runs in a podman container managed by podman's systemd ('quadlet') integration. The configuration for the container is at `~/.config/containers/systemd/zwop-tws.container`:

```ini
[Unit]
Description=ZWOP Token Writer Service

[Container]
Image=ghcr.io/european-xfel/zulip-write-only-proxy-tws:latest
PublishPort=8443:8443
Volume=/home/xdana/work/github.com/European-XFEL/zulip-write-only-proxy/certs:/app/certs
Volume=/gpfs:/gpfs

[Service]
Restart=always

[Install]
WantedBy=default.target
```

The important configurable options are:

- `PublishPort` - should match the config in ZWOP
- `Volume` mount for the certificates - certs should match ZWOP client certs

The service can be managed via user systemd commands and/or podman, e.g:

```bash
# to update after a new release:
## fetch newest image
podman pull ghcr.io/european-xfel/zulip-write-only-proxy-tws:latest

## restart the container
podman restart systemd-zwop-tws  # systemctl --user restart zwop-tws.service

# troubleshooting:
## view logs
podman logs systemd-zwop-tws  # systemctl --user status zwop-tws.service
```

## Todo

Tentative list of things to do in the future:

- [ ] Query MyMdC for the stream name given a proposal number
- [ ] Query MyMdC for the list of topics and pass that on instead of trying to get them with the Zulip API
- [ ] Improve logging (structlog/loguru? sentry?)
- [ ] Set up dependabot
- [ ] Add test step to build-image workflow
- [ ] Allow for configuring zulip bots to use per client
