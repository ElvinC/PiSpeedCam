# PiSpeedCam
Low cost 1000fps high speed camera based on raspberry pi

## Usage
Start server:

`pip3 install -r requirements.txt`

`python main.py`

Open `[Raspbery-pi IP]:8081` in a browser to access the control panel.

## What is this?
High speed footage is cool, but proper high speed cameras cost thousands or tens of thousands of dollars. It turns out that the raspberry pi, when combined with an inexpensive camera module, is capable of recording approximate 1000 fps at a resolution of 640x75 pixels. The result is an imaging system costing less than $100, that can be used experiment with high speed videography.

The "hard work" to make this possible has already been done by namely Herman-SW and 6by9, so check out the following for more technical details: 
* https://github.com/Hermann-SW/fork-raspiraw
* https://github.com/6by9/dcraw

Furthermore RobertElderSoftware has an excellent technical guide on capturing high speed footage using these tools: https://blog.robertelder.org/recording-660-fps-on-raspberry-pi-camera/

The purpose of this repository is to use the existing resources to create an easy to use high speed imaging package. In particular, with the following key features in mind:

* Remote camera monitoring/control with framerate, resolution, exposure etc.
* Live video preview
* Remote trigger interface
* GPIO recording trigger
* File management and processing
* Raw image color adjustments
* Timestamp overlay for time-sensitive video analysis
* Run as service at startup
* 3D printed parts for tripod mounting
* Optional wifi hotspot

This would result in a system that can be rapidly set up for video capture.

## Required hardware
The following are currently used, but others may work as well
* Raspberry Pi V2 camera module (https://www.raspberrypi.com/products/camera-module-v2/)
* Raspberry Pi 3B
