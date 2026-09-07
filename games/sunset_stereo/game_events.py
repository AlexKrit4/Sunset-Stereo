"""Game-specific event helpers for Sunset Stereo.

Stereo Mix uses the standard Stake `updateGlobalMult` event so the
official Web SDK handler map works without a custom bookEvent type.
"""

from src.events.events import update_global_mult_event


def emit_stereo_mix(gamestate):
    """Publish the current Stereo Mix value to the frontend."""
    update_global_mult_event(gamestate)
