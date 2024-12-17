#!/bin/bash
# SPDX-License-Identifier: GPL-2.0
# This script queries the version of Chrome currently listed as available
# in the Google API. It then compares this to the version of Chrome we last
# saw stored in a file. If the version has changed, it updates the file and
# fires off a GitHub Actions `repository_dispatch` event to trigger a new
# Chroimum tarball.

# We use systemd journaling because this typically runs on a VPS with systemd
# and we want to log to the journal. If you're running this on a different
# system, replace the `systemd-cat` command with e.g. `logger`.
set -e

log()
{
	local priority="$1" message="$2"

	# Comment out to log debug messages
	test "_${priority}" != _debug || return 0

	systemd-cat -t check_chromium_versions -p ${priority} <<<${message}
}

log debug "Checking Chromium versions"

# change to script home
pushd "$(dirname "$0")" > /dev/null ||
	(log err "Failed to enter script dir"; exit 1)

rm -f releases.json *.latest.new

curl --fail-with-body --max-time 30 --no-progress-meter -o releases.json \
	'https://versionhistory.googleapis.com/v1/chrome/platforms/linux/channels/all/versions/all/releases?filter=channel%3C=dev&order_by=version%20desc' ||
	(log err "Failed to download Chromium release info"; exit 1)

channels=(stable beta dev)
channels_to_update=()
for channel in "${channels[@]}"; do
	# Get latest version for the given channel
	version=$(jq -r --arg CHANNEL "${channel}" \
		'limit(1; .releases[] | select(.name | test("/channels/" + $CHANNEL + "/")) | .version)' \
		releases.json)
	if [ -z "${version}" ] || [ "_${version}" = _null ]; then
		log warning "${channel}: No version found"
	elif [ ! -f "${channel}.latest" ]; then
		log info "${channel}: No previous version, found ${version}"
		echo "${version}" > "${channel}.latest"
		channels_to_update+=("${channel}")
	elif ! cmp -s "${channel}.latest" - <<<"${version}"; then
		log info "${channel}: New version ${version} found"
		echo "${version}" > "${channel}.latest.new"
		channels_to_update+=("${channel}")
	else
		log debug "${channel}: Version ${version} unchanged"
	fi
done

log debug "Chromium check complete"

if [ ${#channels_to_update[@]} -gt 0 ]; then
	if [[ ! -f ./GITHUB_TOKEN ]]; then
		log err "No GitHub token found"
		exit 1
	fi
	log info "Firing repository_dispatch event"
	if curl -X POST -H "Accept: application/vnd.github.everest-preview+json" \
		-H "Authorization: token $(cat ./GITHUB_TOKEN)" \
		--data '{"event_type": "tag-chromium-versions"}' \
		"https://api.github.com/repos/chromium-linux-tarballs/chromium-tarballs/dispatches"
	then
		for newfile in *.latest.new; do
			test -f ${newfile} || continue
			mv -f ${newfile} ${newfile%.new}
		done
		log info "Updated channels: ${channels_to_update[*]}"
	else
		log err "Failed to fire repository_dispatch event"
	fi
else
	log debug "No channels updated"
fi

popd > /dev/null
