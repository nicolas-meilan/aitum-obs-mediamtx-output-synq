import base64
import hashlib
import json
import os
import signal
import subprocess
import sys
import threading

import obspython as obs
import websocket
from dotenv import load_dotenv


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(SCRIPT_DIR, ".env")

load_dotenv(ENV_FILE)

WS_HOST = os.getenv("WS_HOST", "127.0.0.1")
WS_PORT = int(os.getenv("WS_PORT", "4444"))
WS_PASSWORD = os.getenv("WS_PASSWORD", "")

OUTPUT_NAME = "DELAY"

MEDIAMTX_DIR = os.path.join(
  SCRIPT_DIR,
  "mediamtx"
)

MEDIAMTX_BIN_NAME = (
  "mediamtx.exe"
  if sys.platform == "win32"
  else "mediamtx"
)

MEDIAMTX_BIN = os.path.join(
  MEDIAMTX_DIR,
  MEDIAMTX_BIN_NAME
)

MEDIAMTX_CONFIG = os.path.join(
  MEDIAMTX_DIR,
  "mediamtx.yml"
)

MEDIAMTX_CWD = MEDIAMTX_DIR
MEDIAMTX_STOP_TIMEOUT = 5

RECONNECT_MIN_DELAY = 1
RECONNECT_MAX_DELAY = 30

LOG_PREFIX = "[Aitum MediaMTX]"

EVENTSUB_GENERAL = 1 << 0
EVENTSUB_OUTPUTS = 1 << 6
EVENTSUB_VENDORS = 1 << 9

EVENTSUB_MASK = (
  EVENTSUB_GENERAL
  | EVENTSUB_OUTPUTS
  | EVENTSUB_VENDORS
)

AITUM_VENDOR_NAME = "aitum-stream-suite"

mediamtx_process = None
mediamtx_lock = threading.Lock()

ws_conn = None
ws_thread = None

stop_event = threading.Event()

current_state = None


def log(msg):
  print(f"{LOG_PREFIX} {msg}")


def authenticate(hello):
  auth = hello["d"]["authentication"]

  salt = auth["salt"]
  challenge = auth["challenge"]

  secret = hashlib.sha256(
    (WS_PASSWORD + salt).encode("utf-8")
  ).digest()

  secret_b64 = base64.b64encode(
    secret
  ).decode("utf-8")

  auth_hash = hashlib.sha256(
    (secret_b64 + challenge).encode("utf-8")
  ).digest()

  return base64.b64encode(
    auth_hash
  ).decode("utf-8")


def connect_and_identify():
  ws = websocket.create_connection(
    f"ws://{WS_HOST}:{WS_PORT}",
    timeout=5
  )

  hello = json.loads(
    ws.recv()
  )

  identify = {
    "op": 1,
    "d": {
      "rpcVersion": hello["d"]["rpcVersion"],
      "eventSubscriptions": EVENTSUB_MASK
    }
  }

  if "authentication" in hello["d"]:
    identify["d"]["authentication"] = (
      authenticate(hello)
    )

  ws.send(
    json.dumps(identify)
  )

  identified = json.loads(
    ws.recv()
  )

  if identified.get("op") != 2:
    raise Exception(
      "OBS WebSocket authentication failed"
    )

  return ws


def start_mediamtx():
  global mediamtx_process

  with mediamtx_lock:
    if (
      mediamtx_process is not None
      and mediamtx_process.poll() is None
    ):
      log(
        "mediamtx is already running, "
        "skipping start"
      )
      return

    if not os.path.isfile(MEDIAMTX_BIN):
      log(
        f"ERROR: mediamtx executable not found at "
        f"'{MEDIAMTX_BIN}'"
      )
      return

    if not os.path.isfile(MEDIAMTX_CONFIG):
      log(
        f"ERROR: mediamtx.yml not found at "
        f"'{MEDIAMTX_CONFIG}'"
      )
      return

    cmd = [
      MEDIAMTX_BIN,
      MEDIAMTX_CONFIG
    ]

    kwargs = {
      "cwd": MEDIAMTX_CWD,
      "stdout": subprocess.DEVNULL,
      "stderr": subprocess.DEVNULL,
    }

    if sys.platform == "win32":
      kwargs["creationflags"] = (
        subprocess.CREATE_NO_WINDOW
      )
    else:
      kwargs["preexec_fn"] = os.setsid

    try:
      log(
        f"Starting mediamtx: {cmd} "
        f"(cwd={MEDIAMTX_CWD})"
      )

      mediamtx_process = subprocess.Popen(
        cmd,
        **kwargs
      )

      log(
        f"mediamtx started with PID "
        f"{mediamtx_process.pid}"
      )

    except Exception as e:
      log(
        f"ERROR starting mediamtx: "
        f"{type(e).__name__}: {e}"
      )

      mediamtx_process = None


def stop_mediamtx():
  global mediamtx_process

  with mediamtx_lock:
    if (
      mediamtx_process is None
      or mediamtx_process.poll() is not None
    ):
      log(
        "mediamtx is not running, "
        "nothing to stop"
      )

      mediamtx_process = None

      return

    pid = mediamtx_process.pid

    log(
      f"Stopping mediamtx (PID {pid})..."
    )

    try:
      if sys.platform == "win32":
        mediamtx_process.terminate()
      else:
        os.killpg(
          os.getpgid(pid),
          signal.SIGTERM
        )

      mediamtx_process.wait(
        timeout=MEDIAMTX_STOP_TIMEOUT
      )

      log(
        "mediamtx stopped successfully"
      )

    except subprocess.TimeoutExpired:
      log(
        "mediamtx did not stop in time, "
        "forcing kill"
      )

      try:
        mediamtx_process.kill()

        mediamtx_process.wait(
          timeout=2
        )

        log(
          "mediamtx force-killed successfully"
        )

      except Exception as e:
        log(
          f"ERROR force-killing mediamtx: "
          f"{type(e).__name__}: {e}"
        )

    except Exception as e:
      log(
        f"ERROR stopping mediamtx: "
        f"{type(e).__name__}: {e}"
      )

    finally:
      mediamtx_process = None


def handle_event(msg):
  global current_state

  d = msg.get(
    "d",
    {}
  )

  event_type = d.get(
    "eventType"
  )

  event_data = d.get(
    "eventData",
    {}
  )

  if event_type != "VendorEvent":
    return

  if event_data.get(
    "vendorName"
  ) != AITUM_VENDOR_NAME:
    return

  inner_data = event_data.get(
    "eventData",
    {}
  )

  aitum_event_type = event_data.get(
    "eventType"
  )

  output = inner_data.get(
    "output",
    ""
  )

  log(
    f"Aitum event: "
    f"type={aitum_event_type!r}, "
    f"output={output!r}"
  )

  if aitum_event_type == "start_output":

    if (
      output.strip().lower()
      != OUTPUT_NAME.strip().lower()
    ):
      return

    if current_state is True:
      return

    current_state = True

    log(
      f"Streaming STARTED on "
      f"'{OUTPUT_NAME}'"
    )

    start_mediamtx()

    return

  if aitum_event_type == "stop_output":

    if current_state is False:
      return

    current_state = False

    log(
      f"Streaming STOPPED on "
      f"'{OUTPUT_NAME}'"
    )

    stop_mediamtx()

    return


def listen_loop():
  global ws_conn

  delay = RECONNECT_MIN_DELAY

  while not stop_event.is_set():

    try:
      log(
        f"Connecting to OBS WebSocket "
        f"({WS_HOST}:{WS_PORT})..."
      )

      ws_conn = connect_and_identify()

      log(
        "Connected and subscribed to events."
      )

      delay = RECONNECT_MIN_DELAY

      ws_conn.settimeout(
        1.0
      )

      while not stop_event.is_set():

        try:
          raw = ws_conn.recv()

        except websocket.WebSocketTimeoutException:
          continue

        if not raw:
          raise ConnectionError(
            "Connection closed by OBS"
          )

        try:
          msg = json.loads(
            raw
          )

        except json.JSONDecodeError:
          continue

        if msg.get("op") == 5:
          handle_event(msg)

    except Exception as e:

      if not stop_event.is_set():
        log(
          f"Connection lost/failed: "
          f"{e!r}. "
          f"Retrying in {delay}s..."
        )

    finally:

      if ws_conn:
        try:
          ws_conn.close()
        except Exception:
          pass

        ws_conn = None

    if stop_event.wait(
      delay
    ):
      break

    delay = min(
      delay * 2,
      RECONNECT_MAX_DELAY
    )


def script_load(settings):
  global ws_thread

  print("")
  print(
    f"{LOG_PREFIX} ==========================="
  )
  print(
    f"{LOG_PREFIX} MEDIAMTX AUTO START/STOP"
  )
  print(
    f"{LOG_PREFIX} ==========================="
  )

  if not WS_PASSWORD:
    log(
      "WARNING: WS_PASSWORD is not configured"
    )

  if not os.path.isfile(MEDIAMTX_BIN):
    log(
      f"WARNING: mediamtx not found at "
      f"'{MEDIAMTX_BIN}'"
    )

  if not os.path.isfile(MEDIAMTX_CONFIG):
    log(
      f"WARNING: mediamtx.yml not found at "
      f"'{MEDIAMTX_CONFIG}'"
    )

  log(
    f"WebSocket: {WS_HOST}:{WS_PORT}"
  )

  log(
    f"Watched output: '{OUTPUT_NAME}'"
  )

  log(
    f"MediaMTX executable: "
    f"'{MEDIAMTX_BIN}'"
  )

  log(
    f"MediaMTX config: "
    f"'{MEDIAMTX_CONFIG}'"
  )

  stop_event.clear()

  ws_thread = threading.Thread(
    target=listen_loop,
    daemon=True
  )

  ws_thread.start()


def script_unload():
  log(
    "Unloading script..."
  )

  stop_event.set()

  if ws_conn:
    try:
      ws_conn.close()
    except Exception:
      pass

  if ws_thread:
    ws_thread.join(
      timeout=3
    )

  stop_mediamtx()

  log(
    "Script unloaded."
  )


def script_description():
  return """
Aitum MediaMTX Auto Start/Stop

Monitors the Aitum Stream Suite output "DELAY".

MediaMTX starts when the DELAY output starts
and stops when the output stops.

Expected directory structure:

<script_dir>/
  script.py
  .env
  mediamtx/
    mediamtx.exe
    mediamtx.yml

.env:

WS_HOST
WS_PORT
WS_PASSWORD
"""
