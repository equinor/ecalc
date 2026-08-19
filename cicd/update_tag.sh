#!/usr/bin/env bash

############################
# Usage:
# update_tag.sh <tag> <commit_hash>
# TODO: Consider creating a python script for this as well, since it would be easier to read and maintain.
# but it works...
# TODO: Does it work with immutable releases - NO, because tags cannot be moved in that case! So,
# in that case, should only be run when we have a final release. However, what if we need to patch
# 14.9.0 with 14.9.1, then we would not be able to change the v14 og v14.9 tag. Do we need those
# tags after all or should stick to the full version tags that we set once, and instead
# have logic that correctly sorts the versions and finds the latest one?
# We already have correct logic for comparing versions in version.py, we just
# need to have a list of versions (versions.py or version_service.py?) where we can e.g. add a lot of versions
# with e.g. sha, and then sort and find e.g. the latest one etc.

set -e

tag=$1
commit_hash=$2

# Setup git
git config user.name "eCalc Auto Updater Bot"
git config user.email "<none>"

# Tag commit with tag (remove old, add new)
echo "Removing ${tag} tag remote"
git push origin :refs/tags/${tag} || echo "No tag to delete remotely, ${tag} didn't exist"

echo "Removing ${tag} tag locally"
git tag -d ${tag} || echo "No tag to delete locally, ${tag} didn't exist"

echo "Add ${tag} tag locally"
git tag ${tag} ${commit_hash}

echo "Add ${tag} tag remote"
git push --tags
