import subprocess  # noqa: S404

from hatchling.builders.hooks.plugin.interface import (  # pyright: ignore[reportMissingImports]
    BuildHookInterface,
)


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):  # noqa: ARG002

        subprocess.run(["pnpm", "build"], check=True, cwd=self.root)  # noqa: S607
