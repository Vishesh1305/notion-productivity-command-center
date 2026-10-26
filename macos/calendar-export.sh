#!/bin/zsh
set -euo pipefail
script_dir=${0:A:h}
project_dir=${script_dir:h}
binary_path="$project_dir/build/CalendarExport"
mkdir -p "$project_dir/build"
if [[ ! -x "$binary_path" || "$script_dir/CalendarExport.m" -nt "$binary_path" || "$script_dir/CalendarExport-Info.plist" -nt "$binary_path" ]]; then
  clang -fobjc-arc -O2 "$script_dir/CalendarExport.m" -framework Foundation -framework EventKit \
    -sectcreate __TEXT __info_plist "$script_dir/CalendarExport-Info.plist" -o "$binary_path"
fi
exec "$binary_path" "$@"
