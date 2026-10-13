#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
export DOTNET_ROOT="$root/.local/dotnet"
export DOTNET_CLI_HOME="$root/.local/dotnet-home"
export DOTNET_CLI_TELEMETRY_OPTOUT=1
if [ ! -x "$root/.local/picogk/Kcee.Geometry" ]; then
 echo 'PicoGK not provisioned. See host/macos/picogk/README.md' >&2
 exit 1
fi
exec "$root/.local/picogk/Kcee.Geometry" "$@"
