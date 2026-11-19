
#include <SPI.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7735.h>

// ================= DESKBUDDY CONFIG =================

#define TFT_CS   5
#define TFT_DC   27
#define TFT_RST  26

#define SCREEN_W 128
#define SCREEN_H 160

#define HEADER_H 48
#define GIF_W    128
#define GIF_H    112
#define GIF_Y    48

#define BAUD_RATE 460800
#define CHUNK_SIZE 1024
#define FRAME_SIZE (GIF_W * GIF_H * 2)

#define CHUNK_TIMEOUT 12000

Adafruit_ST7735 tft = Adafruit_ST7735(TFT_CS, TFT_DC, TFT_RST);

uint16_t gifBuffer[GIF_W * GIF_H];

String clockTime = "--:--";
String clockDate = "WAITING FOR PC";

// ================= HEADER =================

void drawHeader() {
  tft.fillRect(0, 0, SCREEN_W, HEADER_H, 0x0841);

  tft.setTextWrap(false);

  // Main clock
  tft.setTextColor(ST77XX_WHITE);
  tft.setTextSize(2);
  tft.setCursor(5, 6);
  tft.print(clockTime);

  // Date
  tft.setTextSize(1);
  tft.setTextColor(0x7DDF);
  tft.setCursor(5, 32);
  tft.print(clockDate);

  // Accent separator
  tft.drawFastHLine(5, 45, 118, 0x05BF);
}

// ================= SERIAL LINE =================

String readCommand() {
  static String command = "";

  while (Serial.available()) {
    char c = Serial.read();

    if (c == '\n') {
      String result = command;
      command = "";
      result.trim();
      return result;
    }

    if (c != '\r' && command.length() < 100) {
      command += c;
    }
  }

  return "";
}

// ================= CLOCK =================

void handleClock(String command) {
  int first = command.indexOf('|');
  int second = command.indexOf('|', first + 1);

  if (first < 0 || second < 0) {
    Serial.println("ERR_CLOCK");
    return;
  }

  clockTime = command.substring(first + 1, second);
  clockDate = command.substring(second + 1);

  drawHeader();

  Serial.println("CLOCK_OK");
}

// ================= RECEIVE EXACT BYTES =================

bool readExactChunk(uint8_t *destination, size_t length) {
  size_t received = 0;
  unsigned long lastByteTime = millis();

  while (received < length) {
    while (Serial.available() && received < length) {
      destination[received++] = Serial.read();
      lastByteTime = millis();
    }

    if (millis() - lastByteTime > CHUNK_TIMEOUT) {
      return false;
    }

    delay(0);
  }

  return true;
}

// ================= RECEIVE GIF FRAME =================

void receiveGifFrame() {
  Serial.println("FRAME_READY");

  uint8_t *rawBuffer = reinterpret_cast<uint8_t *>(gifBuffer);

  size_t remaining = FRAME_SIZE;
  size_t offset = 0;

  while (remaining > 0) {
    size_t chunkLength = min((size_t)CHUNK_SIZE, remaining);

    if (!readExactChunk(rawBuffer + offset, chunkLength)) {
      Serial.println("ERR_TIMEOUT");
      return;
    }

    offset += chunkLength;
    remaining -= chunkLength;

    Serial.println("ACK");
  }

  // Display only after the complete frame has arrived.
  tft.drawRGBBitmap(0, GIF_Y, gifBuffer, GIF_W, GIF_H);

  Serial.println("DONE");
}

// ================= SETUP =================

void setup() {
  Serial.setRxBufferSize(8192);
  Serial.begin(BAUD_RATE);

  SPI.begin(18, -1, 23, TFT_CS);

  tft.initR(INITR_BLACKTAB);
  tft.setRotation(0);
  tft.setSPISpeed(8000000);

  tft.fillScreen(ST77XX_BLACK);

  drawHeader();

  Serial.println("READY");
}

// ================= LOOP =================

void loop() {
  String command = readCommand();

  if (command.length() == 0) {
    return;
  }

  if (command == "G") {
    receiveGifFrame();
  }
  else if (command.startsWith("T|")) {
    handleClock(command);
  }
  else {
    Serial.println("ERR_COMMAND");
  }
}
