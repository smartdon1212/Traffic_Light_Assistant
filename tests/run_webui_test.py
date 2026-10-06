"""Quick test: push a fake frame and event to event_queue and query web_ui via Flask test client.

This script loads `web_ui.py` using importlib (file-based import) so the
Flask `app` instance is accessible when running the script directly.
"""
import os
import sys
import importlib.util
import numpy as np

# Repo root and path setup
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Import event_queue by file path to avoid ModuleNotFoundError
EVENT_Q_PATH = os.path.join(REPO_ROOT, 'event_queue.py')
spec_eq = importlib.util.spec_from_file_location('event_queue', EVENT_Q_PATH)
event_queue = importlib.util.module_from_spec(spec_eq)
spec_eq.loader.exec_module(event_queue)
sys.modules['event_queue'] = event_queue

# Load web_ui.py by file path to avoid import resolution issues
WEB_UI_PATH = os.path.join(REPO_ROOT, 'web_ui.py')
spec = importlib.util.spec_from_file_location('web_ui', WEB_UI_PATH)
web_ui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(web_ui)
app = getattr(web_ui, 'app')


# Create a simple white image
img = (255 * np.ones((240, 320, 3), dtype=np.uint8)).astype('uint8')

# Push frame and an accident event
event_queue.push_frame(img)
event_queue.push_event(
    'accident', {'detected': True, 'severity': 'high', 'confidence': 0.92})

with app.test_client() as c:
    resp = c.get('/api/events')
    print('STATUS:', resp.status_code)
    print(resp.get_data(as_text=True))
