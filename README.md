# SICK LMS500 Lidar Interpretation

![Screenshot](image.jpg)

Real-time point cloud visualiser for the SICK LMS500 LiDAR that works over Serial exposed on USB, rather than Ethernet.  
Reads LMDscandata telegrams over the serial service port, parses them, converts to Cartesian coordinates, and displays a live map with rotation control.

## Features
- Real-time point cloud using pyserial and matplotlib  
- Full LMDscandata parser  
- Rotation slider for alignment
- Cursor readout coordinates

## Requirements
Install dependencies:

pip install pyserial matplotlib numpy

## Usage
1. Connect the LMS500 via USB and identify the COM port.  
2. Set `PORT = "COMx"` in the script.  
3. Run:

python main.py

4. Use the rotation slider to tune as reqiured.
5. Hover the cursor to view coordinates and range.

## NOTE

The LMS500 should be read via Ethernet for high-speed and high-resolution applications. This is a lightweight solution, especially useful for situations where Ethernet is not available.
