# PiSpeedCam
Low cost 1000fps high speed camera based on raspberry pi

## Installation
1. Clone project (including submodules): 
`git clone --recurse-submodules https://github.com/ElvinC/PiSpeedCam.git`

2. Navigate to folder with: `cd PiSpeedCam`
3. Install python dependencies: `pip3 install -r requirements.txt`
4. Build dependencies: `./init.sh`

## Usage
1. (After reboot) run ./dependencies/fork-raspiraw/camera_i2c
2. Start server: `python3 main.py`
3. Open `[Raspbery-pi IP]:8081` in a browser to access the control panel. This can be on a different computer on the same network.
4. Set the desired capture time (max is about 6000 ms with the Raspberry Pi 3) and hit capture. Wait for capture completion and transfer to RAM.
5. Select the newest recording from the dropdown and hit "(re)process recording". With parallel processing this takes about 7 minutes for a 5 second recording.
6. Recording can be played after processing.

Recordings are stored in the `captures` folder as a separete folder for each recording.
Transferring the recording can be done with `scp` or a flash disk. Integrated transfer is work in progress.

For best result, import the PNG sequence directly into a video editor and apply color correction/constrast adjustments.

## What is this?
High speed footage is cool, but proper high speed cameras cost thousands or tens of thousands of dollars. It turns out that the Raspberry Pi, when combined with an inexpensive camera module, is capable of recording approximate 1000 fps at a resolution of 640x75 pixels. The result is an imaging system costing less than $100, that can be used to experiment with high speed videography.

The "hard work" to make this possible has already been done by namely Herman-SW and 6by9, so check out the following for more technical details or more control of what's happening under the hood: 
* https://github.com/Hermann-SW/fork-raspiraw
* https://github.com/6by9/dcraw

Furthermore RobertElderSoftware has an excellent technical guide on capturing high speed footage using these tools: https://blog.robertelder.org/recording-660-fps-on-raspberry-pi-camera/

The purpose of this repository is to use the existing resources to create an easy to use high speed imaging package.

Working features:

* Browser-based client
* Remote camera monitoring/control of recording time/exposure - Working-ish
* File management and processing
* Remote trigger interface
* Video playback
* Preview color histogram and color adjustments 
* Live video preview - semi-working, inactive due to camera lockup problems
* Parallel image decoding

TODO:

* Recording format presets (not all combinations of resolution/framerate work)
* Test on raspberry pi 4 (larger ram size) and other cameras
* Video transfer
* GPIO recording trigger
* Raw image color adjustments
* Timestamp overlay for time-sensitive video analysis
* Run as service at startup
* 3D printed parts for tripod mounting
* Optional wifi hotspot

## Required hardware
The following are currently used for development, but others may work as well
* Raspberry Pi V2 camera module (https://www.raspberrypi.com/products/camera-module-v2/)
* Raspberry Pi 3B
