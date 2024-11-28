#!/bin/bash
# SPDX-License-Identifier: GPL-2.0
# This script queries the version of Chrome currently listed as available
# in the Google API. It then compares this to the version of Chrome we last
# saw stored in a file. If the version has changed, it updates the file and
# fires off a GitHub Actions `repository_dispatch` event to trigger a new
# Chroimum tarball.

# We use systemd journaling because this typically runs on a VPS with systemd
# and we want to log to the journal. If you're running this on a different
# system, remove the `systemd-cat` commands (or replace with `logger`).
set -e

echo "Checking Chromium versions" | systemd-cat -t check_chromium_versions -p info

# change to script home
pushd "$(dirname "$0")" > /dev/null ||
	(echo "Failed to enter script dir" | systemd-cat -t check_chromium_versions -p err && exit 1)

channels=(stable beta dev)
channels_updated=()
for channel in "${channels[@]}"; do
	# We could do something fancy but three webrequests is "fine" and the script was already laying around
	version=$(./get_chromium_versions.py --channel ${channel})
	if [ ! -f "${channel}" ]; then
		echo "${channel}: File does not exist, creating" | systemd-cat -t check_chromium_versions -p info
		echo "${version}" > "${channel}"
		channels_updated+=("${channel}")
		continue
	fi
	if ! diff -q "${channel}" <(echo "${version}") > /dev/null; then
		echo "${channel}: Version changed, updating file" | systemd-cat -t check_chromium_versions -p info
		echo "${version}" > "${channel}"
		echo "Firing repository_dispatch event" | systemd-cat -t check_chromium_versions -p info
		if [[ ! -f ./GITHUB_TOKEN ]]; then
			echo "No GitHub token found" | systemd-cat -t check_chromium_versions -p err
			exit 1
		fi
		if ! curl -X POST -H "Accept: application/vnd.github.everest-preview+json" \
			-H "Authorization: token $(cat ./GITHUB_TOKEN)" \
			--data '{"event_type": "tag-chromium-versions"}' \
			"https://api.github.com/repos/chromium-linux-tarballs/chromium-tarballs/dispatches"; then
				echo "Failed to fire repository_dispatch event" | systemd-cat -t check_chromium_versions -p err
		fi
		channels_updated+=("${channel}")
	else
		echo "${channel}: Version unchanged" | systemd-cat -t check_chromium_versions -p info
	fi
done

echo "Chromium check complete" | systemd-cat -t check_chromium_versions -p info
if [ ${#channels_updated[@]} -gt 0 ]; then
	echo "Updated channels: ${channels_updated[*]}" | systemd-cat -t check_chromium_versions -p info
else
	echo "No channels updated" | systemd-cat -t check_chromium_versions -p info
fi

popd > /dev/null
