#!/bin/sh
set -eu
case_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
artifact_root=$(CDPATH= cd -- "$case_root/../.." && pwd)
exec sh "$artifact_root/replay.sh" --case second-admission/r136
