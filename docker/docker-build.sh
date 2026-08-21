#!/bin/sh -f

if [[ $# -ne 3 ]]; then
    echo Usage: docker-build.sh major minor patch
    exit 1
fi

# Setup
VERSION=$1.$2.$3
DEVELOPMENT_FOLDER=~/Workbench/Development
PROJECT_FOLDER=$DEVELOPMENT_FOLDER/Projects/DailyTaskManager
PUBLISH_FOLDER=$DEVELOPMENT_FOLDER/Docker/dailytaskmanager/dailytaskmanager-$VERSION.0

# Publish the application
cd $PROJECT_FOLDER
rm -fr dist
rm -fr src/daily_task_manager.egg-info
source venv/bin/activate
pip install build
python -m build

# Docker build folder setup
rm -fr $PUBLISH_FOLDER
mkdir -p $PUBLISH_FOLDER
cp $PROJECT_FOLDER/dist/daily_task_manager-$VERSION-py3-none-any.whl $PUBLISH_FOLDER
cp -R $PROJECT_FOLDER/migrations $PUBLISH_FOLDER
cp $PROJECT_FOLDER/src/streamlit_app.py $PUBLISH_FOLDER
cp $PROJECT_FOLDER/docker/Dockerfile $DEVELOPMENT_FOLDER/Docker/dailytaskmanager

# # Docker build
cd $DEVELOPMENT_FOLDER/Docker/dailytaskmanager
docker buildx build --platform linux/amd64 --build-arg VERSION="$VERSION" -t "davewalker5/dailytaskmanager:$VERSION.0" -t davewalker5/dailytaskmanager:latest -f Dockerfile .
