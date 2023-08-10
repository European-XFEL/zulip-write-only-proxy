# Zulip Write Only Proxy

## Usage

### Text Only

Using requests (synchronous):

```python
import requests

url = "http://exfldadev01.desy.de:8089/message"
params = {
    "topic": "test-read-only-thing-2",
    "content": "I recommend muting this topic."
}
headers = {
    "accept": "application/json",
    "X-API-key": "GXXQoc8YlXJv2VDksX2Y7NzQAWdkdNeZ5fFvBLrCe6A",
    "Content-Type": "multipart/form-data"
}

response = requests.post(url, params=params, headers=headers)
```

Using httpx (async):

```python
import httpx

url = "http://exfldadev01.desy.de:8089/message"
params = {
    "topic": "test-read-only-thing-2",
    "content": "I recommend muting this topic."
}
headers = {
    "accept": "application/json",
    "X-API-key": "GXXQoc8YlXJv2VDksX2Y7NzQAWdkdNeZ5fFvBLrCe6A",
    "Content-Type": "multipart/form-data"
}

async with httpx.AsyncClient() as client:
    response = await client.post(url, params=params, headers=headers)
```

### Image/File Upload

Using requests (synchronous):

```python
import requests

url = 'http://exfldadev01.desy.de:8089/message'
headers = {
    'accept': 'application/json',
    'X-API-key': 'DQBMXmA6wmxsQLq4A27GErqD2pARI4IooOciNcmq3ng',
}
params = {
    'content': f'Bonk bonk',
}
files = {'image': open('./downloads/recursion.jpg', 'rb')}

response = requests.post(url, headers=headers, params=params, files=files)
```

Using httpx (async):

```python
import httpx

url = 'http://exfldadev01.desy.de:8089/message'
headers = {
    'accept': 'application/json',
    'X-API-key': 'DQBMXmA6wmxsQLq4A27GErqD2pARI4IooOciNcmq3ng',
}
params = {
    'content': f'Bonk bonk',
}
files = {'image': open('./downloads/recursion.jpg', 'rb')}

async with httpx.AsyncClient() as client:
    response = await client.post(url, headers=headers, params=params, files=files)
```

## Development Setup

For docker:

```sh
# Start server in background
docker compose up -d
```

For CLI:

```sh
# Normal venv:
python3 -m venv .venv
source .venv/bin/activate

python3 -m pip install .

# Poetry:
poetry install
poetry shell

damnit-zulip --help
```

To create a client for proposal 2222:

```sh
damnit-zulip create 2222 "proposal 2222 stream"
```

Default configuration is something like:

```json
{
  "t425dYYQAVAT9AZiPx5fe0nrLzQSPpjZW-54EdxOUPQ": {
    "proposal_no": 2222,
    "stream": "proposal 2222 stream",
  }
}
```

Stream/topic can be edited manually in the JSON file or set via CLI at creation time.

## Deployment Setup

Deployment is similar to development with `docker compose`, but instead a docker stack is used to allow for better scaling and update configuration.

To quickly bring the service up or down run `make up` or `make down`.

Bringing up the service runs:

```sh
docker compose config | docker stack deploy -c - zwop
```

To update the stack, use the same command. This will pull in the latest image and perform a rolling restart of the service, which will first start the new container, wait for a successful health check, and then stop the old container.

A cron job runs the deployment command every minute to check for updates.

NB: There is an outstanding issue with `docker stack deploy` where it [does not load `.env` files](https://github.com/moby/moby/issues/29133) in the same way that `docker compose up` does. This is solved by running `docker compose config` to generate a compose-compliant file (with env vars subsituted) and piping that to `docker stack deploy`.
