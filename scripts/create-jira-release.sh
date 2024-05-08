#!/usr/bin/env bash

set -eou pipefail

release_version=$1
webhook_url=$2

# Create array of sorted tags
mapfile -t tags < <(git tag --list 'v*.*.*' | sort -Vr)

echo "Found tags:"
echo "${tags[@]}"

# Loop array to find previous tag
for ((i=0; i < "${#tags[@]}"; i++)); do
  if [[ "$release_version" = "${tags[$i]}" ]]; then
    previous_tag="${tags[($i + 1)]}"
    break
  fi
done

echo "Found previous release $previous_tag"

mapfile -t issues < <(git log "$previous_tag".."$release_version" | grep -oP 'ECALC-\d+')
issues_json=$(jq --compact-output --null-input '$ARGS.positional' --args -- "${issues[@]}")

# Create webhook body
body=$(jq --arg version "$release_version" --argjson issues_json "$issues_json" -Rn '{"issues": $issues_json|unique, "version": $version}')

echo "$body"

# Trigger webhook
curl -X POST -H 'Content-type: application/json' --silent --output /dev/null --data "$body" "$webhook_url"
