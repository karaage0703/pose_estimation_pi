# pose_estimation_pi
Fast Pose estimation on Raspberry Pi

This repository program and deep learning model file are based on [PINTO_model_zoo](https://github.com/PINTO0309/PINTO_model_zoo).


# Setup
## Hardware

- Raspberry Pi 4 or Raspberry Pi 3(Raspberry Pi 4 is recommended)
- Raspi cam module or Web camera

## Setup deeplearning environment
Execute following commands:

```sh
$ git clone https://github.com/karaage0703/raspberry-pi-setup
$ cd raspberry-pi-setup
$ ./setup-opencv-raspbian-buster.sh
$ ./setup-tensorflow-raspbian-buster.sh
```

## Download this repository
Execute following command:

```sh
$ cd && git clone https://github.com/karaage0703/pose_estimation_pi
```

# Usage
## Pose estimation with raspi cam module
Execute following commands:

```sh
$ cd ~/pose_estimation_pi
$ python3 pose_estimation.py --camera_type=raspi_cam
```

## Pose estimation with web camera
Execute following commands:

```sh
$ cd ~/pose_estimation_pi
$ python3 pose_estimation.py --camera_type=usb_cam
```

## Pose estimation with video file
Execute following commands:

```sh
$ cd ~/pose_estimation_pi
$ python3 pose_estimation.py --input_video_file=<video file name>
```

# License
This software is released under MIT License, see LICENSE.

# Author
- [@PINTO0309](https://github.com/PINTO0309)
- [@karaage0703](http://github.com/karaage0703)

# References
- https://github.com/PINTO0309/PINTO_model_zoo/tree/main/007_mobilenetv2-poseestimation/dm100_224
