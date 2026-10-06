"""Configuration module for Traffic Light Assistant.

This module centralizes all tunable parameters for the traffic light detection
system, making it easy to adjust color thresholds and processing parameters
without modifying core detection logic.
"""

# ============================================================================
# HSV Color Thresholds for Traffic Light Detection
# ============================================================================
# Note: HSV values are normalized as follows:
#   H (Hue): 0-180 in OpenCV (0-360° mapped to 0-180)
#   S (Saturation): 0-255
#   V (Value/Brightness): 0-255

# Red color ranges (exists at both low and high hue values)
RED_LOWER_1 = [0, 120, 50]      # Low hue red
RED_UPPER_1 = [10, 255, 255]
RED_LOWER_2 = [160, 120, 50]    # High hue red
RED_UPPER_2 = [180, 255, 255]

# Yellow color range
YELLOW_LOWER = [15, 120, 50]
YELLOW_UPPER = [35, 255, 255]

# Green color range
GREEN_LOWER = [40, 60, 50]
GREEN_UPPER = [90, 255, 255]

# ============================================================================
# Detection Parameters
# ============================================================================

# Minimum number of pixels to consider as a valid detection
DEFAULT_MIN_AREA = 100

# Enable morphological operations (erosion/dilation) to clean masks
ENABLE_MORPHOLOGY = True

# Kernel size for morphological operations
MORPH_KERNEL_SIZE = 5

# Minimum contour area (in pixels) to be considered a traffic light
MIN_CONTOUR_AREA = 50

# Enable confidence scoring (area ratio between top 2 colors)
ENABLE_CONFIDENCE = True

# Minimum confidence ratio (top_area / second_top_area) to be confident
MIN_CONFIDENCE_RATIO = 1.2

# ============================================================================
# Processing Parameters
# ============================================================================

# Frame resize scale for faster processing (1.0 = no resize)
FRAME_SCALE = 1.0

# Default maximum frames to process (0 = unlimited)
DEFAULT_MAX_FRAMES = 0

# Display FPS counter on video output
SHOW_FPS = True

# ============================================================================
# Logging Parameters
# ============================================================================

# Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL = "INFO"

# Maximum log file size in MB before rotation
LOG_BACKUP_COUNT = 7

# ============================================================================
# Alert System Parameters
# ============================================================================

# Debounce time (seconds) - don't alert for the same color within this window
ALERT_DEBOUNCE_SECONDS = 0.5

# Enable alert system integration
ENABLE_ALERTS = True

# Color to alert on ('red', 'yellow', 'green', or None for all)
ALERT_ON_COLOR = None  # None = alert on any detection

# Emergency / integration endpoints
# Optional HTTP endpoints for emergency dispatch; keep empty by default
EMERGENCY_HTTP_URL_POLICE = ""  # e.g. "https://ops.example.local/dispatch/police"
EMERGENCY_HTTP_URL_AMBULANCE = ""  # e.g. "https://ops.example.local/dispatch/ems"

# Enable traffic controller integration (simulator or hardware)
ENABLE_TRAFFIC_CONTROL = False
TRAFFIC_CONTROL_ENDPOINT = ""  # Optional HTTP endpoint for traffic controller

# Debounce for emergency alerts (seconds)
EMERGENCY_DEBOUNCE_SECONDS = 5.0

# Optional API key for emergency webhooks (will be sent as Authorization: Bearer <key>)
EMERGENCY_HTTP_API_KEY = ""
