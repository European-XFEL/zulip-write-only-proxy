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

## Server Setup and Development

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
