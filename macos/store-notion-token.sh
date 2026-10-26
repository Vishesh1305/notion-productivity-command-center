#!/bin/zsh
set -eu

if [[ ! -t 0 ]]; then
  print -u2 'Run this script in an interactive Terminal window.'
  exit 1
fi

print 'At the Terminal "password:" prompt, paste the Notion API token and press Return; the text stays invisible.'
print 'If macOS separately asks to unlock the login Keychain, use your Mac login password only in that pop-up.'
print 'The token will not be saved in this project.'
/usr/bin/security add-generic-password -a "$USER" -s notion-command-center -U -w
stored_token=$(/usr/bin/security find-generic-password -w -s notion-command-center)
if [[ -z "$stored_token" ]]; then
  print -u2 'The Keychain item is empty. Copy the API token in Notion, rerun this script, paste at the password prompt, and press Return.'
  exit 1
fi
unset stored_token
print 'Notion token stored in your macOS Keychain.'
