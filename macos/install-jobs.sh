#!/bin/zsh
set -euo pipefail

script_dir=${0:A:h}
agent_dir="${HOME}/Library/LaunchAgents"
user_domain="gui/$(/usr/bin/id -u)"

if ! /usr/bin/security find-generic-password -s notion-command-center >/dev/null 2>&1; then
  print -u2 'Store the Notion token with macos/store-notion-token.sh first.'
  exit 1
fi

if [[ ! -x "$script_dir/run-job.sh" ]]; then
  print -u2 'macos/run-job.sh is missing or not executable.'
  exit 1
fi

for name in calendar recurrence metric; do
  source_plist="$script_dir/com.vishesh.command-center.$name.plist.example"
  /usr/bin/plutil -lint "$source_plist" >/dev/null
done

/bin/mkdir -p "$agent_dir"
for name in calendar recurrence metric; do
  label="com.vishesh.command-center.$name"
  target_plist="$agent_dir/$label.plist"
  if [[ -f "$target_plist" ]]; then
    /bin/launchctl bootout "$user_domain/$label" >/dev/null 2>&1 || true
  fi
  /bin/cp "$script_dir/$label.plist.example" "$target_plist"
  /usr/bin/plutil -replace ProgramArguments.0 -string "$script_dir/run-job.sh" "$target_plist"
  /usr/bin/plutil -lint "$target_plist" >/dev/null
  /bin/chmod 600 "$target_plist"
  /bin/launchctl bootstrap "$user_domain" "$target_plist"
  print "Installed $label"
done

print 'All user LaunchAgents are installed and will run at login.'
