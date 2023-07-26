from pathlib import Path

import zulip

ZULIP_CLIENT: zulip.Client


def setup():
    global ZULIP_CLIENT
    ZULIP_CLIENT = zulip.Client(config_file=str(Path(__file__).parent / "zuliprc"))


async def get_client():
    return ZULIP_CLIENT
