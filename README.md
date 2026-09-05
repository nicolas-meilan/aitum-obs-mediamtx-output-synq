# Aitum MediaMTX Auto Start/Stop

Automatically starts and stops a local MediaMTX server based on the state of the `DELAY` output in Aitum Stream Suite.

The script runs inside OBS Studio, connects to the OBS WebSocket server, listens for Aitum Stream Suite vendor events, and automatically launches or stops MediaMTX when the configured `DELAY` output starts or stops.

## Table of Contents

* [How It Works](#how-it-works)
* [Requirements](#requirements)
* [Project Structure](#project-structure)
* [Installation](#installation)

  * [1. Install Python 3.12](#1-install-python-312)
  * [2. Install Python Dependencies](#2-install-python-dependencies)
  * [3. Download MediaMTX](#3-download-mediamtx)
  * [4. Configure MediaMTX](#4-configure-mediamtx)
  * [5. Configure the Environment](#5-configure-the-environment)
  * [6. Configure OBS WebSocket](#6-configure-obs-websocket)
  * [7. Configure Aitum Stream Suite](#7-configure-aitum-stream-suite)
  * [8. Configure the DELAY Output](#8-configure-the-delay-output)
  * [9. Configure Python in OBS](#9-configure-python-in-obs)
  * [10. Add the Script to OBS](#10-add-the-script-to-obs)
  * [11. Verify That the Script Loaded](#11-verify-that-the-script-loaded)
  * [12. Test MediaMTX](#12-test-mediamtx)
* [How the Script Detects Aitum Events](#how-the-script-detects-aitum-events)
* [Start Behavior](#start-behavior)
* [Stop Behavior](#stop-behavior)
* [Duplicate Event Protection](#duplicate-event-protection)
* [OBS WebSocket Reconnection](#obs-websocket-reconnection)
* [OBS WebSocket Authentication](#obs-websocket-authentication)
* [MediaMTX Process Management](#mediamtx-process-management)
* [Windows Behavior](#windows-behavior)
* [Script Unload Behavior](#script-unload-behavior)
* [Logs](#logs)
* [Troubleshooting](#troubleshooting)

  * [`ModuleNotFoundError: No module named 'websocket'`](#modulenotfounderror-no-module-named-websocket)
  * [`ModuleNotFoundError: No module named 'dotenv'`](#modulenotfounderror-no-module-named-dotenv)
  * [OBS Cannot Load the Python Script](#obs-cannot-load-the-python-script)
  * [`mediamtx.exe not found`](#mediamtxexe-not-found)
  * [`mediamtx.yml not found`](#mediamtxyml-not-found)
  * [MediaMTX Does Not Start](#mediamtx-does-not-start)
  * [OBS WebSocket Connection Failed](#obs-websocket-connection-failed)
  * [Authentication Failed](#authentication-failed)
  * [The Script Connects but MediaMTX Does Not Start](#the-script-connects-but-mediamtx-does-not-start)
  * [Aitum Events Are Received but Ignored](#aitum-events-are-received-but-ignored)
  * [MediaMTX Starts but Does Not Stop](#mediamtx-starts-but-does-not-stop)
* [Reloading the Script](#reloading-the-script)
* [Restarting OBS](#restarting-obs)
* [Security](#security)
* [Dependencies](#dependencies)
* [Directory Resolution](#directory-resolution)
* [Complete Example](#complete-example)
* [Complete Startup Flow](#complete-startup-flow)
* [Important Notes](#important-notes)
* [Official OBS Documentation](#official-obs-documentation)

---

## How It Works

```text
Aitum Stream Suite

       |
       | start_output
       v

OBS WebSocket

       |
       | VendorEvent
       v

OBS Python Script

       |
       | start
       v

MediaMTX

       |
       | RTMP / HLS / WebRTC
       v

Local streaming pipeline
```

When the Aitum output named `DELAY` starts:

```text
Aitum DELAY output
        |
        v
   start_output
        |
        v
 OBS WebSocket
        |
        v
 Python script
        |
        v
 Start MediaMTX
```

When the `DELAY` output stops:

```text
Aitum DELAY output
        |
        v
    stop_output
        |
        v
 OBS WebSocket
        |
        v
 Python script
        |
        v
 Stop MediaMTX
```

The script only reacts to the output named:

```text
DELAY
```

The output name comparison is case-insensitive and ignores surrounding whitespace.

---

## Requirements

* OBS Studio with Python scripting support
* Python 3.12
* Aitum Stream Suite
* OBS WebSocket
* MediaMTX
* `websocket-client`
* `python-dotenv`

Python dependencies are defined in:

```text
requirements.txt
```

### Important

`obspython` is **not** installed through pip.

It is provided by OBS Studio when the script is executed by OBS.

---

## Project Structure

The expected project structure is:

```text
aitum-mediamtx/
│
├── aitum-mediamtx.py
├── requirements.txt
├── .env
├── .gitignore
├── README.md
│
└── mediamtx/
    ├── mediamtx.exe
    └── mediamtx.yml
```

On Windows, the MediaMTX executable must be:

```text
mediamtx.exe
```

The script automatically detects the executable according to the operating system.

---

# Installation

## 1. Install Python 3.12

Install Python 3.12 for Windows.

Make sure the Python installation architecture matches your OBS installation.

For example:

```text
C:\Users\<username>\AppData\Local\Programs\Python\Python312
```

You can verify Python from PowerShell:

```powershell
& "C:\Users\<username>\AppData\Local\Programs\Python\Python312\python.exe" --version
```

Expected output:

```text
Python 3.12.x
```

### OBS Python compatibility

OBS must be configured to use the same Python installation.

The Python directory configured in OBS should be the installation directory, not the executable itself.

For example, this is correct:

```text
C:\Users\<username>\AppData\Local\Programs\Python\Python312
```

---

## 2. Install Python Dependencies

Open PowerShell in the repository directory.

For example:

```powershell
cd D:\OBS\obsScripts\aitum-mediamtx
```

Install the dependencies:

```powershell
& "C:\Users\<username>\AppData\Local\Programs\Python\Python312\python.exe" -m pip install -r requirements.txt
```

The required packages are:

```text
websocket-client
python-dotenv
```

You can verify them with:

```powershell
& "C:\Users\<username>\AppData\Local\Programs\Python\Python312\python.exe" -m pip show websocket-client
```

```powershell
& "C:\Users\<username>\AppData\Local\Programs\Python\Python312\python.exe" -m pip show python-dotenv
```

---

## 3. Download MediaMTX

Download MediaMTX for your operating system.

For Windows, the project should contain:

```text
mediamtx.exe
```

Place the executable inside:

```text
mediamtx/
```

The resulting path should be:

```text
aitum-mediamtx/
└── mediamtx/
    └── mediamtx.exe
```

The script automatically looks for:

```text
<script_directory>/mediamtx/mediamtx.exe
```

It does not require MediaMTX to be installed globally.

---

## 4. Configure MediaMTX

Place your MediaMTX configuration file inside:

```text
mediamtx/mediamtx.yml
```

The final structure should therefore be:

```text
mediamtx/
├── mediamtx.exe
└── mediamtx.yml
```

The script launches MediaMTX using:

```text
mediamtx.exe mediamtx.yml
```

The working directory is also set to:

```text
mediamtx/
```

This allows MediaMTX to resolve relative paths and configuration resources correctly.

---

## 5. Configure the Environment

Create a file named:

```text
.env
```

in the repository root:

```text
aitum-mediamtx/
├── aitum-mediamtx.py
├── .env
└── mediamtx/
```

Example:

```env
WS_HOST=127.0.0.1
WS_PORT=4444
WS_PASSWORD=your_obs_websocket_password
```

### Configuration

| Variable      | Description            | Default     |
| ------------- | ---------------------- | ----------- |
| `WS_HOST`     | OBS WebSocket host     | `127.0.0.1` |
| `WS_PORT`     | OBS WebSocket port     | `4444`      |
| `WS_PASSWORD` | OBS WebSocket password | empty       |

The script uses these values to connect to OBS WebSocket.

---

## 6. Configure OBS WebSocket

Open OBS Studio.

Go to:

```text
Tools → WebSocket Server Settings
```

Enable:

```text
Enable WebSocket server
```

The default WebSocket port is usually:

```text
4444
```

Make sure the port matches:

```env
WS_PORT=4444
```

If OBS is using another port, change `.env` accordingly.

If authentication is enabled, put the same password in:

```env
WS_PASSWORD=your_password
```

The script automatically performs the OBS WebSocket authentication handshake.

You do not need to manually generate the authentication hash.

---

## 7. Configure Aitum Stream Suite

Install and configure Aitum Stream Suite in OBS.

The script listens specifically for Aitum vendor events.

The expected vendor name is:

```text
aitum-stream-suite
```

The script reacts to these Aitum events:

```text
start_output
stop_output
```

The monitored output is:

```text
DELAY
```

Therefore, Aitum Stream Suite must contain an output named:

```text
DELAY
```

For example:

```text
Outputs

├── Main
├── Twitch
└── DELAY
```

The script does not react to other outputs.

---

## 8. Configure the DELAY Output

The output must be named:

```text
DELAY
```

The comparison is case-insensitive, so these names are also accepted:

```text
delay
Delay
DELAY
```

The script also ignores leading and trailing whitespace.

For example:

```text
 DELAY
```

is treated as:

```text
DELAY
```

However, a different output name such as:

```text
DELAYED
```

will not trigger the script.

---

## 9. Configure Python in OBS

Open OBS Studio.

Go to:

```text
Tools → Scripts
```

Open the:

```text
Python Settings
```

tab.

Set the Python installation path to your Python 3.12 installation directory.

For example:

```text
C:\Users\<username>\AppData\Local\Programs\Python\Python312
```

### Important

Select the **Python installation directory**.

Do not select:

```text
python.exe
```

For example, this is correct:

```text
C:\Users\<username>\AppData\Local\Programs\Python\Python312
```

This is incorrect:

```text
C:\Users\<username>\AppData\Local\Programs\Python\Python312\python.exe
```

OBS uses this Python installation to load Python scripts.

---

## 10. Add the Script to OBS

Once Python is configured, remain in:

```text
Tools → Scripts
```

Open the:

```text
Scripts
```

tab.

Click:

```text
+
```

Select:

```text
aitum-mediamtx.py
```

OBS will load the script.

You do **not** need to run the `.py` file manually.

The script must be loaded by OBS.

---

## 11. Verify That the Script Loaded

After adding the script, open:

```text
Tools → Scripts
```

and verify that:

```text
aitum-mediamtx.py
```

appears in the list.

The script should immediately create a background thread that connects to OBS WebSocket.

The OBS Script Log should show something similar to:

```text
[Aitum MediaMTX] ===========================
[Aitum MediaMTX] MEDIAMTX AUTO START/STOP
[Aitum MediaMTX] ===========================
[Aitum MediaMTX] WebSocket: 127.0.0.1:4444
[Aitum MediaMTX] Watched output: 'DELAY'
[Aitum MediaMTX] MediaMTX executable: '...\mediamtx\mediamtx.exe'
[Aitum MediaMTX] MediaMTX config: '...\mediamtx\mediamtx.yml'
[Aitum MediaMTX] Connecting to OBS WebSocket (127.0.0.1:4444)...
[Aitum MediaMTX] Connected and subscribed to events.
```

If you see:

```text
Connected and subscribed to events.
```

the connection to OBS WebSocket was successful.

---

## 12. Test MediaMTX

Before testing the Aitum integration, verify that MediaMTX itself can start correctly.

The expected executable is:

```text
mediamtx/mediamtx.exe
```

and the configuration is:

```text
mediamtx/mediamtx.yml
```

From PowerShell:

```powershell
cd .\mediamtx
.\mediamtx.exe .\mediamtx.yml
```

If MediaMTX starts correctly, stop it with:

```text
Ctrl+C
```

The script will later start and stop it automatically.

---

## How the Script Detects Aitum Events

OBS WebSocket sends events to the script.

The script first checks that the event is:

```text
VendorEvent
```

Then it checks:

```text
vendorName == "aitum-stream-suite"
```

The script then reads the Aitum event type.

The relevant event types are:

```text
start_output
stop_output
```

The output name is extracted from the event.

Only:

```text
DELAY
```

is processed.

---

## Start Behavior

When Aitum reports:

```text
start_output
```

for:

```text
DELAY
```

the script changes its internal state to:

```text
True
```

and starts MediaMTX.

The log should show:

```text
[Aitum MediaMTX] Aitum event: type='start_output', output='DELAY'
[Aitum MediaMTX] Streaming STARTED on 'DELAY'
[Aitum MediaMTX] Starting mediamtx: [...]
[Aitum MediaMTX] mediamtx started with PID 12345
```

---

## Stop Behavior

When Aitum reports:

```text
stop_output
```

for:

```text
DELAY
```

the script changes its internal state to:

```text
False
```

and stops MediaMTX.

Example:

```text
[Aitum MediaMTX] Aitum event: type='stop_output', output='DELAY'
[Aitum MediaMTX] Streaming STOPPED on 'DELAY'
[Aitum MediaMTX] Stopping mediamtx (PID 12345)...
[Aitum MediaMTX] mediamtx stopped successfully
```

---

## Duplicate Event Protection

The script keeps track of the current state.

If the script already knows that the output is running:

```text
current_state = True
```

another `start_output` event will not start another MediaMTX process.

Likewise, if the output is already stopped:

```text
current_state = False
```

another `stop_output` event will not attempt to stop MediaMTX again.

This prevents duplicate MediaMTX processes and unnecessary stop operations.

---

## OBS WebSocket Reconnection

The script automatically reconnects if the OBS WebSocket connection is lost.

The retry delay starts at:

```text
1 second
```

and increases exponentially up to:

```text
30 seconds
```

The sequence is approximately:

```text
1s
2s
4s
8s
16s
30s
30s
...
```

After a successful connection, the retry delay is reset to:

```text
1 second
```

---

## OBS WebSocket Authentication

If OBS WebSocket authentication is enabled, the script automatically performs the authentication process.

It uses:

```text
WS_PASSWORD
```

from `.env`.

The authentication process uses the OBS WebSocket challenge and salt to calculate the required authentication response.

No authentication hash needs to be manually configured.

---

## MediaMTX Process Management

The script keeps a reference to the MediaMTX process.

Before starting MediaMTX, it checks whether the process is already running.

If it is already running:

```text
[Aitum MediaMTX] mediamtx is already running, skipping start
```

No second MediaMTX process is created.

When stopping MediaMTX, the script waits up to:

```text
5 seconds
```

for the process to terminate normally.

If MediaMTX does not stop within that period, the script forces the process to terminate.

---

## Windows Behavior

On Windows, MediaMTX is started with:

```text
CREATE_NO_WINDOW
```

This prevents an additional console window from appearing when MediaMTX is launched.

The MediaMTX process runs in the background.

The script expects:

```text
mediamtx.exe
```

---

## Script Unload Behavior

When the script is unloaded from OBS, it performs a cleanup sequence.

It:

1. Signals the WebSocket listener to stop.
2. Closes the OBS WebSocket connection.
3. Waits for the listener thread.
4. Stops MediaMTX if it is running.
5. Releases the process reference.

Example:

```text
[Aitum MediaMTX] Unloading script...
[Aitum MediaMTX] Stopping mediamtx (PID 12345)...
[Aitum MediaMTX] mediamtx stopped successfully
[Aitum MediaMTX] Script unloaded.
```

---

## Logs

The script uses the OBS Script Log.

All messages use the prefix:

```text
[Aitum MediaMTX]
```

Example:

```text
[Aitum MediaMTX] ===========================
[Aitum MediaMTX] MEDIAMTX AUTO START/STOP
[Aitum MediaMTX] ===========================
[Aitum MediaMTX] WebSocket: 127.0.0.1:4444
[Aitum MediaMTX] Watched output: 'DELAY'
[Aitum MediaMTX] Connected and subscribed to events.
```

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'websocket'`

The `websocket-client` package was installed into a different Python installation than the one OBS is using.

Check:

```text
Tools → Scripts → Python Settings
```

Then install the dependency using that same Python installation:

```powershell
& "C:\Users\<username>\AppData\Local\Programs\Python\Python312\python.exe" -m pip install websocket-client
```

Or reinstall everything:

```powershell
& "C:\Users\<username>\AppData\Local\Programs\Python\Python312\python.exe" -m pip install -r requirements.txt
```

### `ModuleNotFoundError: No module named 'dotenv'`

Install `python-dotenv` into the Python installation configured in OBS:

```powershell
& "C:\Users\<username>\AppData\Local\Programs\Python\Python312\python.exe" -m pip install python-dotenv
```

Or:

```powershell
& "C:\Users\<username>\AppData\Local\Programs\Python\Python312\python.exe" -m pip install -r requirements.txt
```

### OBS Cannot Load the Python Script

Check all of the following:

* Python 3.12 is installed.
* Python is configured under `Tools → Scripts → Python Settings`.
* The configured path points to the Python installation directory.
* You did not select `python.exe` itself.
* Python architecture matches OBS architecture.
* The script has a `.py` extension.
* OBS has been restarted after changing Python settings.

### `mediamtx.exe not found`

The script expects:

```text
mediamtx/
└── mediamtx.exe
```

relative to the Python script.

For example:

```text
aitum-mediamtx/
├── aitum-mediamtx.py
└── mediamtx/
    └── mediamtx.exe
```

The log will show the exact path it is looking for.

### `mediamtx.yml not found`

The script expects:

```text
mediamtx/
└── mediamtx.yml
```

Make sure the configuration file is located next to `mediamtx.exe`.

### MediaMTX Does Not Start

First test MediaMTX manually:

```powershell
cd .\mediamtx
.\mediamtx.exe .\mediamtx.yml
```

If MediaMTX reports a configuration error, fix `mediamtx.yml` before testing the OBS integration.

Also check whether another MediaMTX instance is already using the required ports.

### OBS WebSocket Connection Failed

Check:

```env
WS_HOST=127.0.0.1
WS_PORT=4444
WS_PASSWORD=your_password
```

Verify that OBS WebSocket is enabled.

Also verify that the port configured in OBS matches:

```env
WS_PORT
```

The script will automatically retry the connection if it fails.

### Authentication Failed

Check the password in:

```env
WS_PASSWORD=your_password
```

It must match the password configured in OBS WebSocket.

If the OBS WebSocket password was changed, update `.env` and reload the script.

### The Script Connects but MediaMTX Does Not Start

Check the Script Log.

You should see:

```text
Connected and subscribed to events.
```

Then start the Aitum output named:

```text
DELAY
```

The script should log:

```text
Aitum event: type='start_output', output='DELAY'
```

If this event does not appear, verify:

* Aitum Stream Suite is running.
* The output is actually named `DELAY`.
* The output is being started through Aitum.
* Aitum is generating the expected vendor event.
* OBS WebSocket is connected.

### Aitum Events Are Received but Ignored

If the log contains an event for another output, for example:

```text
[Aitum MediaMTX] Aitum event: type='start_output', output='MAIN'
```

the script will ignore it.

Only:

```text
DELAY
```

is monitored.

### MediaMTX Starts but Does Not Stop

Check that Aitum generates:

```text
stop_output
```

when the `DELAY` output stops.

The log should contain:

```text
[Aitum MediaMTX] Aitum event: type='stop_output', output='DELAY'
```

If the event appears but MediaMTX remains running, check the subsequent log messages for process termination errors.

---

## Reloading the Script

If you modify the Python script while OBS is running:

1. Open OBS.
2. Go to:

```text
Tools → Scripts
```

3. Select the script.
4. Reload the script.

Alternatively, remove and add the script again.

When the script is unloaded, it attempts to stop MediaMTX automatically.

---

## Restarting OBS

After configuring Python for the first time, it is recommended to restart OBS.

After restarting OBS:

1. OBS loads the configured Python installation.
2. OBS loads the saved script.
3. The script starts its WebSocket listener.
4. The script connects to OBS WebSocket.
5. The script starts listening for Aitum events.

You do not need to manually execute the Python script.

---

## Security

The `.env` file contains the OBS WebSocket password.

Do not commit it to Git.

Add `.env` to `.gitignore`:

```text
.env
```

Never publish your OBS WebSocket password.

If the password is accidentally exposed, change it in:

```text
OBS → Tools → WebSocket Server Settings
```

and update `.env`.

---

## Dependencies

The project uses:

```text
websocket-client>=1.8.0,<2.0.0
python-dotenv>=1.0.0,<2.0.0
```

`obspython` is provided by OBS Studio and must not be installed through pip.

Standard Python modules used by the script include:

```text
base64
hashlib
json
os
signal
subprocess
sys
threading
```

These are part of Python's standard library.

---

## Directory Resolution

The script determines its own directory:

```python
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
```

MediaMTX paths are then resolved relative to the script.

Therefore:

```text
MEDIAMTX_DIR
```

points to:

```text
<script_directory>/mediamtx
```

and the executable is:

```text
<script_directory>/mediamtx/mediamtx.exe
```

The configuration file is:

```text
<script_directory>/mediamtx/mediamtx.yml
```

This makes the project portable.

You can move the entire project directory to another location without changing the MediaMTX paths.

---

## Complete Example

A complete Windows installation can look like:

```text
D:\OBS\obsScripts\aitum-mediamtx\
│
├── aitum-mediamtx.py
├── requirements.txt
├── .env
├── .gitignore
├── README.md
│
└── mediamtx\
    ├── mediamtx.exe
    └── mediamtx.yml
```

`.env`:

```env
WS_HOST=127.0.0.1
WS_PORT=4444
WS_PASSWORD=your_obs_websocket_password
```

OBS:

```text
Tools
└── Scripts
    ├── Python Settings
    │   └── C:\Users\<username>\AppData\Local\Programs\Python\Python312
    │
    └── Scripts
        └── aitum-mediamtx.py
```

Aitum:

```text
Output name:

DELAY
```

MediaMTX:

```text
mediamtx/
├── mediamtx.exe
└── mediamtx.yml
```

---

## Complete Startup Flow

When everything is configured, the complete flow is:

```text
OBS starts
    |
    v
Python script loads
    |
    v
Read .env
    |
    v
Connect to OBS WebSocket
    |
    v
Authenticate
    |
    v
Subscribe to Aitum vendor events
    |
    v
Wait for events
```

When `DELAY` starts:

```text
Aitum
  |
  | start_output
  v
OBS WebSocket
  |
  v
Python Script
  |
  | output == DELAY
  v
MediaMTX starts
```

When `DELAY` stops:

```text
Aitum
  |
  | stop_output
  v
OBS WebSocket
  |
  v
Python Script
  |
  | output == DELAY
  v
MediaMTX stops
```

---

## Important Notes

* The script does not start MediaMTX when OBS itself starts.
* MediaMTX is started only after receiving the appropriate Aitum `start_output` event for `DELAY`.
* MediaMTX is stopped when the corresponding `stop_output` event is received.
* The script automatically reconnects to OBS WebSocket if the connection is lost.
* Only one MediaMTX process is managed by the script.
* MediaMTX must be located in the project's `mediamtx` directory.
* `mediamtx.yml` must be located next to `mediamtx.exe`.
* `.env` must remain private.
* `obspython` is supplied by OBS and is not a pip dependency.

---

## Official OBS Documentation

For OBS Python scripting and WebSocket configuration, consult the official OBS documentation.

* OBS Python/Lua Scripting Documentation
* OBS Scripting Guide
* OBS Developer Guide

The script is designed to run as an OBS Python script and should be loaded through:

```text
Tools → Scripts
```

rather than executed directly from PowerShell.
