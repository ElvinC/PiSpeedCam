#!/bin/bash

# Get submodules
echo "Installing dependencies..."
git submodule update --init --recursive

# Build dcraw fork
# https://github.com/6by9/dcraw

sudo apt-get install libjasper-dev libjpeg8-dev gettext liblcms2-dev
cd ./dependencies/dcraw/
echo "Building dcraw..."
./buildme
cd ..
cd fork-raspiraw
echo "Building fork-raspiraw"
./buildme
cd ..
cd ..
echo "Installing python dependencies"
pip3 install -r requirements.txt

chmod +x ./scripts/raspiraw_trigger.sh
