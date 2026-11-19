# DeskMate — ESP32 Desktop Companion

A mini desktop companion built using Python and ESP32 that displays the current time, date, and animated GIFs on a TFT screen, helping reduce distractions from constantly checking your phone or computer.

## Features

- Live clock displaying the current time
- Date display with day, month, and year
- Animated GIF playback on the TFT display
- Load GIFs using direct image URLs
- Python desktop application for controlling the display
- Serial communication between Python and ESP32
- Automatic GIF resizing to fit the TFT screen
- RGB565 image conversion for ESP32 compatibility
- Chunk-based image transmission with ACK confirmation
- Separate display sections for time/date and GIF playback
- Play and stop controls for GIF animation
- Compact desktop-friendly design

## Built With

- Python
- Tkinter
- Pillow (PIL)
- PySerial
- C++
- ESP32
- ST7735 TFT Display
- Arduino IDE

## Hardware Requirements

- ESP32-WROOM-32
- ST7735 TFT Display (128 × 160)
- USB cable for programming and serial communication
- Jumper wires

## Installation

Install the required Python libraries:

```bash
python -m pip install pillow pyserial
```

Install the required Arduino libraries through Arduino IDE:

- Adafruit GFX Library
- Adafruit ST7735 and ST7789 Library

## Hardware Connections

| ST7735 Display | ESP32 |
|---|---|
| CS | GPIO 5 |
| DC | GPIO 27 |
| RST | GPIO 26 |
| SCK | GPIO 18 |
| MOSI | GPIO 23 |
| VCC | 3.3V |
| GND | GND |

## Setup

1. Connect the ST7735 display to the ESP32 using the connections above.
2. Open the Arduino sketch in Arduino IDE.
3. Select your ESP32 board and the correct COM port.
4. Upload the firmware to the ESP32.
5. Open the Python application.
6. Enter the ESP32 serial port (for example, COM3).
7. Connect to the ESP32 and load a direct GIF URL.

## Run the Application

Run the Python application from your Python environment:

```bash
python DeskMate.py
```

Replace `DeskMate.py` with your actual Python filename.

## How It Works

1. The Python application downloads and processes the selected GIF.
2. Each GIF frame is resized to 128 × 112 pixels.
3. The image is converted into RGB565 format.
4. Python sends the frame to the ESP32 through serial communication.
5. The ESP32 receives the image in smaller chunks and acknowledges each chunk.
6. The completed frame is displayed on the ST7735 TFT.
7. The clock and date are periodically synchronized from Python.

## Display Layout

- **Top 30%:** Live time and date.
- **Bottom 70%:** Animated GIF display.

## Project Structure

```text
DeskMate/
├── DeskMate.py
├── DeskMate.ino
└── README.md
```

This is an example project structure. Replace the filenames with your actual filenames.

## Future Improvements

- Wi-Fi-based weather information
- More GIF playback controls
- Improved image transmission speed
- Custom clock themes and display styles
- Automatic GIF screen saver
- Better power management

## Author

**Prateesraj K**  
Electronics and Communication Engineering  
Coimbatore Institute of Technology

---

*DeskMate is currently a prototype project, with more improvements planned.*
