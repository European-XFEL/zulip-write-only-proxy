# Zulip Write Only Proxy

## Quick Start

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
damnit-zulip create 2222
```

Default configuration is something like:

```json
{
  "t425dYYQAVAT9AZiPx5fe0nrLzQSPpjZW-54EdxOUPQ": {
    "proposal_no": 222,
    "stream": "some-pattern-222",
    "topic": "some-pattern-222"
  }
}
```

Can stream/topic edited manually or set via CLI at creation time.
