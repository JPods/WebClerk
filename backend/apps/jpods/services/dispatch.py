"""
JPods dispatch service — sends a trip command to the selected network.

  dispatch_sketchup()    → POST localhost:5051/dispatch   (SketchUp WEBrick server)
  dispatch_route_time()  → POST localhost:5050/api/trip/dispatch  (Route-Time Flask)
  dispatch_physical()    → TODO: Natalie inbound API on RPi

Called by TravelView after Alice posts the invoice.
All dispatchers are fire-and-log: a failure does not cancel the invoice.
"""

from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error
from typing import Any

logger = logging.getLogger(__name__)

SKETCHUP_URL    = "http://localhost:5051/dispatch"
ROUTE_TIME_URL  = "http://localhost:5050/api/trip/dispatch"
TIMEOUT_S       = 3


def _post_json(url: str, payload: dict) -> dict:
    """POST JSON to a local service. Returns {ok, status, data} or {ok: False, error}."""
    body = json.dumps(payload).encode()
    req  = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            data = json.loads(resp.read().decode())
            return {"ok": True, "status": resp.status, "data": data}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "status": exc.code, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def dispatch_sketchup(trip: dict[str, Any]) -> dict:
    """Send trip to SketchUp WEBrick server (localhost:5051).

    SketchUp plugin must be running with the WEBrick server started.
    See: readmes/37-jpods-sketchup-dispatch-server.md
    """
    result = _post_json(SKETCHUP_URL, trip)
    if result["ok"]:
        logger.info("SketchUp dispatch ok: %s→%s", trip.get("origin_station_id"), trip.get("destination_station_id"))
    else:
        logger.warning("SketchUp dispatch failed: %s", result.get("error"))
    return result


def dispatch_route_time(trip: dict[str, Any]) -> dict:
    """Send trip to Route-Time (localhost:5050) for travel-time preview.

    Route-Time returns the estimated travel time from the last simulation
    for this O-D pair, and queues the trip for display.
    """
    result = _post_json(ROUTE_TIME_URL, trip)
    if result["ok"]:
        logger.info("Route-Time dispatch ok: %s→%s", trip.get("origin_station_id"), trip.get("destination_station_id"))
    else:
        logger.warning("Route-Time dispatch failed: %s", result.get("error"))
    return result


def dispatch_physical(trip: dict[str, Any]) -> dict:
    """Send trip to Natalie on the physical RPi.

    TODO: build Natalie's inbound dispatch API on the RPi.
    Placeholder returns a not-yet-built notice without failing.
    """
    logger.info(
        "Physical dispatch queued (Natalie inbound API not yet built): %s→%s",
        trip.get("origin_station_id"), trip.get("destination_station_id"),
    )
    return {"ok": False, "error": "Physical dispatch not yet built — Natalie inbound API pending"}


DISPATCHERS = {
    "sketchup":   dispatch_sketchup,
    "physical":   dispatch_physical,
    "route-time": dispatch_route_time,
}


def dispatch(target: str, trip: dict[str, Any]) -> dict:
    """Call the right dispatcher for the selected network target."""
    fn = DISPATCHERS.get(target.lower())
    if fn is None:
        return {"ok": False, "error": f"Unknown dispatch target: {target!r}"}
    return fn(trip)
