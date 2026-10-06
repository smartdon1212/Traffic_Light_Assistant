"""Small Flask-based web UI for reviewing detections and confirming emergency actions.

Provides:
- / : live feed from main.py detection pipeline with event queue
- /api/events (GET) : fetch recent detection events
- /api/confirm (POST) : operator confirms an emergency alert
- /analyze?img=... : analyze static image with current detectors

Run:
    python web_ui.py

This is intentionally minimal and meant for local operator verification.
"""
from pathlib import Path
import json
import logging
import os

try:
    from flask import Flask, request, render_template_string, redirect, url_for, jsonify
except Exception:
    Flask = None

try:
    import event_queue
except Exception:
    event_queue = None

app = Flask(__name__) if Flask is not None else None
logger = logging.getLogger(__name__)

# Attempt to import modules; fall back gracefully
try:
    import accident_detector
except Exception:
    accident_detector = None
try:
    import alert_system
except Exception:
    alert_system = None
try:
    import traffic_control
except Exception:
    traffic_control = None
try:
    import model_detector
    md = model_detector.get_detector()
except Exception:
    md = None

IMAGES_DIR = Path(__file__).parent / 'images'

HOME_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Traffic Light Assistant - Live Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        .panel {
            background: white;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            padding: 20px;
            overflow: hidden;
        }
        .panel h2 {
            color: #333;
            margin-bottom: 15px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        .frame-viewer {
            position: relative;
            background: #000;
            border-radius: 4px;
            overflow: hidden;
            aspect-ratio: 16/9;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #666;
            font-size: 14px;
        }
        .frame-viewer img {
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
        }
        .frame-viewer.waiting {
            background: linear-gradient(45deg, #f0f0f0 25%, transparent 25%, transparent 75%, #f0f0f0 75%, #f0f0f0),
                        linear-gradient(45deg, #f0f0f0 25%, transparent 25%, transparent 75%, #f0f0f0 75%, #f0f0f0);
            background-size: 40px 40px;
            background-position: 0 0, 20px 20px;
            background-color: #e0e0e0;
        }
        .event-list {
            max-height: 600px;
            overflow-y: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .event-item {
            padding: 12px;
            border-bottom: 1px solid #eee;
            font-size: 13px;
            transition: background 0.2s;
        }
        .event-item:last-child { border-bottom: none; }
        .event-item:hover { background: #f9f9f9; }
        .event-type {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 3px;
            font-weight: bold;
            margin-right: 8px;
            font-size: 11px;
        }
        .event-type.accident { background: #ff6b6b; color: white; }
        .event-type.light { background: #4ecdc4; color: white; }
        .event-type.track { background: #95e1d3; color: #333; }
        .event-time {
            color: #999;
            font-size: 11px;
            float: right;
        }
        .event-data {
            margin-top: 8px;
            color: #666;
            line-height: 1.4;
        }
        .confirm-button {
            width: 100%;
            padding: 15px;
            margin-top: 15px;
            background: linear-gradient(135deg, #ff6b6b, #ff8c42);
            color: white;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
        }
        .confirm-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(255, 107, 107, 0.3);
        }
        .confirm-button:active {
            transform: translateY(0);
        }
        .confirm-button:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
        }
        .status-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px;
            background: #f5f5f5;
            border-radius: 4px;
            margin-bottom: 15px;
            font-size: 12px;
        }
        .status-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 5px;
        }
        .status-indicator.active { background: #4caf50; }
        .status-indicator.waiting { background: #ffc107; }
        .no-events {
            text-align: center;
            color: #999;
            padding: 40px 20px;
        }
        @media (max-width: 1024px) {
            .container { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="panel">
            <h2>Live Detection Feed</h2>
            <div class="frame-viewer waiting" id="frameViewer">
                <div>Waiting for frames...</div>
            </div>
            <div class="status-bar">
                <div>
                    <span class="status-indicator waiting" id="statusDot"></span>
                    <span id="statusText">Connecting...</span>
                </div>
                <div id="fpsCounter">FPS: --</div>
            </div>
            <button class="confirm-button" id="confirmBtn" disabled onclick="confirmAlert()">
                ⚠️ Confirm & Notify Emergency
            </button>
        </div>
        <div class="panel">
            <h2>Detection Events</h2>
            <div class="event-list" id="eventList">
                <div class="no-events">No events yet. Monitoring...</div>
            </div>
        </div>
    </div>

    <script>
        let lastFrameTime = 0;
        let frameCount = 0;
        const pollInterval = 500; // Poll every 500ms (2x per second)
        let hasAccidentEvent = false;

        // Poll for new events and frames
        function pollEvents() {
            fetch('/api/events')
                .then(resp => resp.json())
                .then(data => {
                    updateEventList(data.events || []);
                    updateFrameViewer(data.latest_frame);
                    updateStatus(data.events.length > 0);
                })
                .catch(err => {
                    console.error('Error polling events:', err);
                    updateStatus(false);
                });
        }

        function updateEventList(events) {
            const eventList = document.getElementById('eventList');
            hasAccidentEvent = false;

            if (events.length === 0) {
                eventList.innerHTML = '<div class="no-events">No events yet. Monitoring...</div>';
                return;
            }

            let html = '';
            events.forEach(evt => {
                const typeClass = evt.type.toLowerCase();
                const timeStr = new Date(evt.timestamp).toLocaleTimeString();
                
                if (evt.type === 'accident') {
                    hasAccidentEvent = true;
                }

                html += `<div class="event-item">
                    <div>
                        <span class="event-type ${typeClass}">${evt.type.toUpperCase()}</span>
                        <span class="event-time">${timeStr}</span>
                    </div>
                    <div class="event-data">
                        ${JSON.stringify(evt.data).substring(0, 150)}...
                    </div>
                </div>`;
            });
            eventList.innerHTML = html;
            
            // Enable confirm button only if accident detected
            document.getElementById('confirmBtn').disabled = !hasAccidentEvent;
        }

        function updateFrameViewer(frameData) {
            const viewer = document.getElementById('frameViewer');
            if (frameData) {
                viewer.innerHTML = `<img src="data:image/jpeg;base64,${frameData}" />`;
                
                // Update FPS counter
                const now = performance.now();
                if (lastFrameTime > 0) {
                    frameCount++;
                    if (frameCount >= 10) {
                        const elapsed = (now - lastFrameTime) / 1000;
                        const fps = (frameCount / elapsed).toFixed(1);
                        document.getElementById('fpsCounter').textContent = `FPS: ${fps}`;
                        frameCount = 0;
                        lastFrameTime = now;
                    }
                } else {
                    lastFrameTime = now;
                }
            }
        }

        function updateStatus(hasEvents) {
            const dot = document.getElementById('statusDot');
            const text = document.getElementById('statusText');
            if (hasEvents) {
                dot.className = 'status-indicator active';
                text.textContent = 'Live • Events detected';
            } else {
                dot.className = 'status-indicator waiting';
                text.textContent = 'Monitoring • No events';
            }
        }

        function confirmAlert() {
            if (!hasAccidentEvent) {
                alert('No accident event to confirm!');
                return;
            }
            
            if (!confirm('Confirm emergency alert? This will notify authorities and control traffic lights.')) {
                return;
            }

            fetch('/api/confirm', { method: 'POST' })
                .then(resp => resp.json())
                .then(data => {
                    alert('Emergency alert sent: ' + (data.message || 'Check logs'));
                    // Refresh events
                    pollEvents();
                })
                .catch(err => {
                    alert('Error sending alert: ' + err);
                });
        }

        // Start polling
        pollEvents();
        setInterval(pollEvents, pollInterval);
    </script>
</body>
</html>
'''

ANALYZE_HTML = '''
<!doctype html>
<title>Analyze {{ img }}</title>
<h1>Analyze: {{ img }}</h1>
<img src="/static/{{ img }}" width="600"><br>
<p><b>Traffic light:</b> {{ tl_result }}</p>
<p><b>Accident heuristic (red+motion):</b> {{ acc_heuristic }}</p>
<p><b>Model overlap:</b> {{ acc_model }}</p>
<p><b>Track-based:</b> {{ acc_tracks }}</p>
<form action="/send_alert" method="post">
  <input type="hidden" name="img" value="{{ img }}">
  <input type="hidden" name="severity" value="{{ severity }}">
  <button type="submit">Confirm Emergency & Notify</button>
</form>
<p><a href="/">Back</a></p>
'''


@app.route('/')
def index():
    if app is None:
        return 'Flask not installed'
    return render_template_string(HOME_HTML)


@app.route('/api/events')
def api_events():
    """Return recent events and latest frame from event_queue.

    Returns:
        {
            "events": [
                {
                    "type": "accident" | "light" | "track",
                    "timestamp": "ISO8601",
                    "data": {...}
                }
            ],
            "latest_frame": "base64_jpeg_or_null"
        }
    """
    if event_queue is None:
        return jsonify({'events': [], 'latest_frame': None})

    try:
        events = event_queue.get_latest_events(max_count=20)
        latest_frame = event_queue.get_latest_frame()

        return jsonify({
            'events': events,
            'latest_frame': latest_frame
        })
    except Exception as e:
        logger.exception('Error fetching events')
        return jsonify({'events': [], 'latest_frame': None, 'error': str(e)}), 500


@app.route('/health')
def health():
    """Simple health endpoint for monitoring."""
    return jsonify({'ok': True, 'status': 'ready'})


@app.route('/api/confirm', methods=['POST'])
def api_confirm():
    """Operator confirms emergency alert.

    Triggers:
    - send_emergency_alert() via alert_system
    - handle_emergency() via traffic_control
    """
    if event_queue is None:
        return jsonify({'ok': False, 'message': 'Event queue not available'}), 500

    try:
        # Optional auth: if UI_AUTH_TOKEN is configured, require Authorization header
        ui_token = os.environ.get('UI_AUTH_TOKEN')
        if ui_token:
            auth = request.headers.get('Authorization', '')
            if not auth.startswith('Bearer ') or auth.split('Bearer ')[1].strip() != ui_token:
                return jsonify({'ok': False, 'message': 'Unauthorized'}), 403

        # Push confirmation to queue (main.py can read if desired)
        try:
            # signature: push_confirmation(confirmed: bool, event_id: Optional[int], operator: str)
            event_queue.push_confirmation(
                True, event_id=None, operator='operator')
        except Exception:
            logger.debug('Failed to push confirmation to queue', exc_info=True)

        # Trigger alert and control immediately as well (best-effort)
        if alert_system is not None and hasattr(alert_system, 'send_emergency_alert'):
            alert_system.send_emergency_alert(
                'high', location='web_ui', extra={'source': 'operator_confirmation'})

        if traffic_control is not None and hasattr(traffic_control, 'handle_emergency'):
            traffic_control.handle_emergency()

        return jsonify({'ok': True, 'message': 'Emergency alert confirmed and sent'})
    except Exception as e:
        logger.exception('Error in operator confirmation')
        return jsonify({'ok': False, 'message': str(e)}), 500


@app.route('/analyze')
def analyze():
    """Legacy: analyze static image for testing."""
    if app is None:
        return 'Flask not installed'
    img = request.args.get('img')
    p = IMAGES_DIR / img
    if not p.exists():
        return f'Image not found: {img}', 404

    import cv2
    frame = cv2.imread(str(p))

    tl_res = ('unknown', 0.0)
    try:
        from main import detect_traffic_light_color
        tl_res = detect_traffic_light_color(frame)
    except Exception:
        tl_res = ('unknown', 0.0)

    acc_heur = (False, 'low', 0.0)
    try:
        if accident_detector is not None and hasattr(accident_detector, 'detect_accident'):
            acc_heur = accident_detector.detect_accident(frame)
    except Exception:
        acc_heur = (False, 'low', 0.0)

    acc_model = (False, 'low', 0.0)
    try:
        if accident_detector is not None and hasattr(accident_detector, 'detect_accident_with_model'):
            acc_model = accident_detector.detect_accident_with_model(frame)
    except Exception:
        acc_model = (False, 'low', 0.0)

    acc_tracks = (False, 'low', 0.0)
    try:
        # For a single image we can still run model->tracker by creating fake sequence of 1
        if md is not None and tracker_available():
            dets = md.detect(frame, conf=0.25)
            from tracker import Tracker
            tr = Tracker()
            tracks = tr.update(dets)
            if accident_detector is not None and hasattr(accident_detector, 'detect_accident_from_tracks'):
                acc_tracks = accident_detector.detect_accident_from_tracks(
                    tracks)
    except Exception:
        acc_tracks = (False, 'low', 0.0)

    # Choose a severity to pre-fill confirmation
    severity = 'high' if acc_model[0] or acc_tracks[0] else acc_heur[1]

    ANALYZE_HTML = '''
    <!doctype html>
    <title>Analyze {{ img }}</title>
    <h1>Analyze: {{ img }}</h1>
    <img src="/static/{{ img }}" width="600"><br>
    <p><b>Traffic light:</b> {{ tl_result }}</p>
    <p><b>Accident heuristic (red+motion):</b> {{ acc_heuristic }}</p>
    <p><b>Model overlap:</b> {{ acc_model }}</p>
    <p><b>Track-based:</b> {{ acc_tracks }}</p>
    <p><a href="/">Back to Live Dashboard</a></p>
    '''

    return render_template_string(ANALYZE_HTML, img=img, tl_result=f"{tl_res[0]} ({tl_res[1]:.2f})",
                                  acc_heuristic=f"{acc_heur[0]} {acc_heur[1]} ({acc_heur[2]:.2f})",
                                  acc_model=f"{acc_model[0]} {acc_model[1]} ({acc_model[2]:.2f})",
                                  acc_tracks=f"{acc_tracks[0]} {acc_tracks[1]} ({acc_tracks[2]:.2f})",
                                  severity=severity)


def tracker_available():
    try:
        import tracker
        return True
    except Exception:
        return False


if __name__ == '__main__':
    if app is None:
        print('Flask not installed. Install with: pip install flask')
    else:
        # Serve static images folder via Flask static route
        static_folder = str(IMAGES_DIR)
        # set static folder on app, works for this minimal usage
        app.static_folder = static_folder
        app.run(host='0.0.0.0', port=5000, debug=False)
