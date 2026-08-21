#!/bin/sh -f

if [[ $# -ne 3 ]]; then
    echo Usage: docker-push.sh major minor patch
    exit 1
fi

# Push the version and the latest tag to Docker hub
VERSION=$1.$2.$3
docker push davewalker5/dailytaskmanager:$VERSION.0
docker push davewalker5/dailytaskmanager:latest
