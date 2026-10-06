# Traffic Light Assistant 🚦

A lightweight, color-based traffic light detection system that can recognize red, yellow, and green traffic lights from camera feeds, video files, or static images. Perfect for quick testing and demos.

## ✨ Features

- **Real-time Detection**: Analyze live camera feeds or video files
- **Multiple Input Sources**: Support for webcam, video files, and images
- **HSV-based Recognition**: Robust color thresholds in HSV color space
- **Morphological Operations**: Erosion and dilation for cleaner mask processing
- **Confidence Scoring**: Quantified confidence in each detection (0.0-1.0)
- **Debouncing**: Prevents alert spam with configurable debounce window
- **FPS Monitoring**: Real-time performance tracking
- **Comprehensive Logging**: File-based rotating logs for offline inspection
- **Alert System**: Extensible alerting via HTTP webhooks or email
- **Easy Configuration**: Centralized `config.py` for all tunable parameters

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip

### Installation

```powershell
# Install dependencies
python -m pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Try on an image
python main.py --source images/img.jpg --no-show
```

## 📖 Usage Examples

**Detect from camera (default):**
```powershell
python main.py
```

**Detect from video file:**
```powershell
python main.py --source path/to/video.mp4
```

**Detect from image file:**
```powershell
python main.py --source images/traffic_light.jpg
```

**Advanced options:**
```powershell
python main.py --source <input> [--no-show] [--min-area N] [--max-frames N]
```

| Option | Description | Default |
|--------|-------------|---------|
| `--source, -s` | Camera index, video path, or image path | `0` |
| `--no-show` | Disable OpenCV display window | Enabled |
| `--min-area` | Minimum pixels for valid detection | `100` |
| `--max-frames` | Exit after N frames (0 = unlimited) | `0` |

## ⚙️ Configuration

All parameters are in `config.py`. Adjust:

- **Color Thresholds**: `RED_*`, `YELLOW_*`, `GREEN_*` ranges
- **Detection**: `DEFAULT_MIN_AREA`, `ENABLE_MORPHOLOGY`, `MIN_CONFIDENCE_RATIO`
- **Performance**: `SHOW_FPS`, `ENABLE_ALERTS`, `ALERT_DEBOUNCE_SECONDS`

### Alert Backends

**HTTP Webhook:**
```powershell
$env:ALERT_HTTP_URL = "http://localhost:8000/alert"
python main.py --source camera
```

**Email (via local SMTP relay):**
```powershell
$env:ALERT_EMAIL_TO = "user@example.com"
$env:ALERT_EMAIL_FROM = "robot@example.com"
$env:ALERT_SMTP_SERVER = "localhost:25"
python main.py --source camera
```

## 📊 Output

**Console/Log output:**
```
2025-11-11 14:23:45 INFO Frame 0: detected=red (confidence=87.5%)
2025-11-11 14:23:45 INFO Frame 1: detected=red (confidence=89.2%)
```

**Video display:**
- Detected color and confidence percentage
- Real-time FPS counter
- Live feed

**Log files:**
- `logs/app.log` - Application events (7-day rotating)
- `logs/alerts.log` - Alert history

## 🧪 Testing

```powershell
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=main
```

**Coverage:**
- ✅ Red, yellow, green detection
- ✅ Empty frame handling
- ✅ Small area filtering
- ✅ Multiple color disambiguation

## 📁 Project Structure

```
main.py                   # Core detection engine & entry point
config.py                 # Centralized configuration (NEW)
traffic_light_module.py   # ML-ready wrapper for future model integration
vision_module.py          # Vision API stub
alert_system.py           # Alert handling (logging, HTTP, email)
tests/test_detection.py   # Comprehensive unit tests (IMPROVED)
```

## 🎯 What's New (v2.0)

✨ **Improvements:**
- ✅ Added `config.py` for centralized parameter management
- ✅ Morphological operations (erosion/dilation) for cleaner detection
- ✅ Confidence scoring with ratio-based calculation
- ✅ Alert debouncing to prevent spam
- ✅ FPS performance counter
- ✅ Better logging with frame counts
- ✅ Expanded test suite (6 tests covering edge cases)
- ✅ Comprehensive README with examples
- ✅ Better error messages and debugging info

## 🔧 Troubleshooting

**Detection not working?**
- Check lighting conditions
- Adjust HSV thresholds in `config.py`
- Lower `--min-area` for small lights
- Enable debug logging: Set `LOG_LEVEL = "DEBUG"` in config.py

**Camera not opening?**
```powershell
python -c "import cv2; print(cv2.VideoCapture(0).isOpened())"
```

**Performance issues?**
- Set `SHOW_FPS = False` in config.py
- Set `ENABLE_MORPHOLOGY = False` to skip filtering

## 📦 Requirements

- `opencv-python>=4.5.5`
- `numpy>=1.21`
- `pytest>=7.0`

## 🚀 Next Steps

- Integrate with ML model (replace heuristic in `traffic_light_module.py`)
- Add temporal filtering (Kalman filters)
- Support multiple traffic lights per frame
- Auto white-balance calibration

## 📝 Files of Interest

- `main.py` - Core detection logic
- `config.py` - **NEW** - Tunable parameters
- `vision_module.py` - API wrapper for model integration
- `traffic_light_module.py` - Model stub (ready for ML)
- `alert_system.py` - Alert backends (HTTP, email, logging)
- `tests/test_detection.py` - **EXPANDED** - 6 comprehensive tests

---

**Version:** 2.0 (Improved)  
**Last Updated:** November 11, 2025
