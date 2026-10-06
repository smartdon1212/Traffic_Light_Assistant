"""Simple traffic controller stub.

Provides a conservative interface to 'control' traffic lights during an
emergency. In a real deployment this would call an API to the traffic signal
controller hardware or a central traffic management system.

APIs:
- set_light_state(state: str) -> bool
- handle_emergency() -> dict

Keep everything best-effort and non-blocking.
"""
import logging
from typing import Dict

logger = logging.getLogger(__name__)


def set_light_state(state: str) -> bool:
    """Set the traffic light state.

    state: one of 'red', 'yellow', 'green', 'blinking', 'off'
    Returns True if the action was (likely) successful.
    """
    # For now this is a stub that logs the request. Integrate with
    # `TRAFFIC_CONTROL_ENDPOINT` (HTTP) in config for real hardware.
    logger.info("Traffic control: set state=%s", state)
    return True


def handle_emergency() -> Dict[str, str]:
    """Apply an emergency pattern to the lights to allow emergency services
    or to control traffic safely around an incident.

    Returns a summary dict describing actions taken.
    """
    # Simple strategy for demo: set all directions to red, then enable
    # blinking mode for the direction where emergency will pass.
    set_light_state("red")
    # In a real system we'd determine which direction to give priority.
    set_light_state("blinking")
    logger.info("Traffic control: emergency pattern applied")
    return {"status": "ok", "action": "red_then_blinking"}
