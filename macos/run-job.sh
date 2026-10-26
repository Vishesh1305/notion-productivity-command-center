#!/bin/zsh
set -eu

script_dir=${0:A:h}
project_dir=${script_dir:h}
api_key=$(/usr/bin/security find-generic-password -w -s notion-command-center)
if [[ -z "$api_key" ]]; then
  print -u2 'Notion command center credential is unavailable in Keychain.'
  exit 1
fi
export NOTION_API_KEY="$api_key"
export PYTHONPATH="$project_dir/src"
cd "$project_dir"
exec /opt/homebrew/bin/python3 -m command_center.cli "$1"
