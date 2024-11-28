#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# This script will pull any (Desktop) releases of Chromium from the Google Chrome Releases
# API (http://versionhistory.googleapis.com/) and output the version numbers.
# We will then then tag

import argparse, datetime, json, urllib.request

channels = ["stable", "beta", "dev"]


def getChromeVersionData(base_url: str, os: str, channel: str) -> tuple[str, str, str]:
    """
    Fetches the latest Chrome version data for a given operating system and channel.

    Args:
        base_url (str): The base URL for the Chrome version data API.
        os (str): The operating system for which to fetch the Chrome version (e.g., 'linux', 'win', 'mac').
        channel (str): The release channel for which to fetch the Chrome version (e.g., 'stable', 'beta', 'dev').

    Returns:
        tuple: ((str),(str))
            The latest Chrome version for the specified operating system and channel.
            .e.g. ('130.0.6723.116', '2024-11-05T18:08:09.964878Z')

    Raises:
        URLError: If there is an issue with the URL or network connection.
        JSONDecodeError: If the response data is not valid JSON.
        KeyError: If the expected keys are not found in the response data.
    """
    if not base_url.endswith("/"):
        url = base_url + "/"
    # Only fetch the latest release; remove the filter to get all releases
    url += f"{os}/channels/{channel}/versions/all/releases?filter=endtime=1970-01-01T00:00:00Z"
    try:
        response = urllib.request.urlopen(url)
        data = json.loads(response.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"Error: URL not found (404) - {url}")
        else:
            print(f"HTTP error occurred: {e}")
        return None
    except urllib.error.URLError as e:
        print(f"Failed to reach the server: {e.reason}")
        return None

    return data["releases"][0]["version"], data["releases"][0]["serving"]["startTime"]


def getSpecificChromeVersionData(base_url: str, os: str, version: str) -> tuple[str, str, str]:
    """
    Iterates over the history of Chrome version data and retrieves a specific version.

    Args:
        base_url (str): The base URL for the Chrome version data API.
        os (str): The operating system for which to fetch the Chrome version (e.g., 'linux', 'win', 'mac').
        channel (str): The release channel for which to fetch the Chrome version (e.g., 'stable', 'beta', 'dev').

    Returns:
        tuple: ((str),(str))
            The latest Chrome version for the specified operating system and channel.
            .e.g. ('130.0.6723.116', '2024-11-05T18:08:09.964878Z')

    Raises:
        URLError: If there is an issue with the URL or network connection.
        JSONDecodeError: If the response data is not valid JSON.
        KeyError: If the expected keys are not found in the response data.
    """
    for channel in channels:
        if not base_url.endswith("/"):
            url = base_url + "/"
        url += f"{os}/channels/{channel}/versions/all/releases"
        try:
            response = urllib.request.urlopen(url)
            data = json.loads(response.read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"Error: URL not found (404) - {url}")
            else:
                print(f"HTTP error occurred: {e}")
            return None
        except urllib.error.URLError as e:
            print(f"Failed to reach the server: {e.reason}")
            return None

        for release in data["releases"]:
            if release["version"] == version:
                return release["version"], release["serving"]["startTime"], channel

    raise Exception(f"Version {version} not found.")

def main():
    """
    Main function to parse command-line arguments and fetch Chrome version data.

    This function sets up an argument parser to accept a '--hours' argument, which
    specifies the number of hours to look back for Chrome releases. It then iterates
    over a list of Chrome channels, fetching version data for each channel and
    accumulating the results in a list.

    Command-line Arguments:
    --channel (-c) (str): Print only the specified channel.
    --hours (int): Number of hours to look back for Chrome releases (default: 48).
    --verbose (-v): Print verbose output.
    --version (-V) (str): Print only the specified version.

    Prints:
    A list of Chrome version data for the specified channels and time range.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--channel', '-c', type=str)
    parser.add_argument('--hours', type=int, default=48,
                        help='Number of hours to look back for Chrome releases')
    parser.add_argument('--verbose', '-v', action='store_true')
    parser.add_argument('--version', '-V', type=str)
    args = parser.parse_args()

    base = 'https://versionhistory.googleapis.com/v1/chrome/platforms'

    versions: list[tuple] = []

    if args.channel is not None:
        _ver, _date = _ver, _date = getChromeVersionData(base_url=base, os="linux", channel=args.channel)
        versions.append((_ver, _date, args.channel))
    elif args.version is not None:
        _ver, _date, _channel = getSpecificChromeVersionData(base_url=base, os="linux", version=args.version)
        versions.append((_ver, _date, _channel))
    else:
        for channel in channels:
            _ver, _date = getChromeVersionData(base_url=base, os="linux", channel=channel)
            versions.append((_ver, _date, channel))

    if args.version is not None or args.channel is not None:
        datestring = datetime.datetime.strptime(versions[0][1], "%Y-%m-%dT%H:%M:%S.%fZ")
        datestring = datestring.strftime("%B %d, %Y at %I:%M UTC")
        print(f"Chromium {versions[0][0]}: {versions[0][2]} ({datestring})")
    else:
        for chromium in versions:
            datestring = datetime.datetime.strptime(chromium[1], "%Y-%m-%dT%H:%M:%S.%fZ")
            if datestring > datetime.datetime.now() - datetime.timedelta(hours=args.hours):
                if args.verbose:
                    datestring = datestring.strftime("%B %d, %Y at %I:%M UTC")
                    print(f"Chromium {chromium[2]}: {chromium[0]} ({datestring})")
                else:
                    print(chromium[0])


if __name__ == "__main__":
    main()
