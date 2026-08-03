# R&S TS-RSP GPIB Controller

> A FastAPI backend + PySide6 GUI for real-time GPIB control of the **Rohde & Schwarz TS-RSP RF System Platform** switching matrix.

---

## Overview

This tool provides a two-component control stack for the R&S TS-RSP chassis — an RF switching matrix used in EMC, antenna, and RF path-switching test setups:

| Component | File | Description |
|---|---|---|
| **REST API** | `app.py` | FastAPI server that communicates with the TS-USM I/O board over GPIB via PyVISA |
| **GUI** | `gui.py` | PySide6 desktop application inspired by the R&S EMS-K1/ES-K1 software |
| **Path Config** | `paths.json` | Persistent storage for named relay path presets |

The GUI communicates with the API over localhost HTTP, which in turn issues `WD` (Write Data) commands to the TS-USM board over GPIB. Since the TS-USM board does **not** support register readback, all relay states are tracked in an internal software buffer.

---

## Supported Plug-in Modules

The following TS-RSP plug-in boards are configured and supported:

| Module | Relay Type | Relays | Description |
|---|---|---|---|
| **RSP-EMS** | SPDT | K1–K7, K10–K13 | Two-path relays for EMS setups |
| **RSP-EMI** | SPDT | K20–K25 | Two-path relays for EMI setups |
| **RSP-BRF** | SP6T | K31–K34 | Six-path broadband RF switching |
| **RSP-MMF** | SP6T / SP5T | K21–K24 | Multi-path millimeter-wave switching |
| **RSP-MMS** | SPDT | K1–K10 | Two-path millimeter-wave switching |

> **Hardware Note:** SP6T/multi-path relays enforce **mutual exclusion** — only one path per relay can be active at a time. The software automatically calculates and applies the appropriate clearing bitmask on each command.

---

## Architecture

```
┌──────────────────────┐      HTTP/REST      ┌────────────────────────┐
│   gui.py (PySide6)   │ ──────────────────► │   app.py (FastAPI)     │
│                      │  localhost:8001      │                        │
│  Board selector      │                      │  TSRSP_Controller      │
│  Relay toggle boxes  │                      │  - State buffer        │
│  Path presets list   │ ◄────────────────── │  - WD command builder  │
└──────────────────────┘    JSON responses    └────────────┬───────────┘
                                                           │ PyVISA
                                                           ▼
                                               ┌───────────────────────┐
                                               │  TS-USM I/O Board     │
                                               │  (GPIB0::3::INSTR)    │
                                               │  6 x 8-bit registers  │
                                               │  OC0–OC3, REL0–REL1   │
                                               └───────────────────────┘
```

---

## Requirements

- Python 3.10+
- A GPIB interface recognized by PyVISA (e.g., NI-VISA with a USB-GPIB adapter)
- The TS-USM board at its default address (`GPIB0::3::INSTR`)

Install all Python dependencies:

```bash
pip install -r requirements.txt
```

Key packages: `fastapi`, `uvicorn`, `pyvisa`, `pyvisa-py`, `PySide6`, `requests`, `pydantic`

> **Simulation Mode:** If no GPIB hardware is detected, the API automatically falls back to simulation mode — all commands are printed to the console without hardware access. This allows GUI development and testing without a connected instrument.

---

## Usage

### 1. Start the API server

```bash
uvicorn app:app --host 0.0.0.0 --port 8001
```

The server starts on `http://localhost:8001`. On startup it initializes the state buffer for any connected GPIB instrument.

### 2. Launch the GUI

In a separate terminal:

```bash
python gui.py
```

The GUI opens and automatically sends a **Global Initialization Sequence**, zeroing all six hardware registers (`0x90`–`0x95`) to a known clean state.

---

## GUI Features

| Feature | Description |
|---|---|
| **Board Selector** | Switch between RSP-EMS, RSP-EMI, RSP-BRF, RSP-MMF, and RSP-MMS plug-ins |
| **Relay Grid** | Per-relay control blocks with enable checkbox and NC/NO or path radio buttons |
| **Live API Calls** | Every relay toggle immediately posts to the API — no "Apply" button needed |
| **Path Presets** | Save and recall named relay configurations persisted to `paths.json` |
| **Clear / Initialize** | Resets all hardware registers and syncs GUI to a clean state |

---

## API Reference

Base URL: `http://localhost:8001`

### `GET /state`

Returns the current buffered register state for a given GPIB address.

```
GET /state?gpib_address=GPIB0::3::INSTR
```

**Response:**
```json
{
  "0x90": "0x00",
  "0x91": "0x00",
  "0x92": "0x00",
  "0x93": "0x00",
  "0x94": "0x02",
  "0x95": "0x00"
}
```

---

### `POST /initialize`

Resets all relay registers to `0x00` for the specified GPIB address.

**Request body:**
```json
{ "gpib_address": "GPIB0::3::INSTR" }
```

---

### `POST /relay/set`

Toggles a single relay bit on a given register. The optional `clear_mask` field is used for SP6T mutual exclusion — it clears all bits in the mask before applying the new state.

**Request body:**
```json
{
  "gpib_address": "GPIB0::3::INSTR",
  "register": "0x95",
  "bit_value": "0x02",
  "state": true,
  "clear_mask": "0xff"
}
```

**Response:**
```json
{
  "status": "success",
  "gpib": "GPIB0::3::INSTR",
  "register": "0x95",
  "new_value": "0x02"
}
```

---

### `POST /path/switch/{path_name}`

Activates a named macro path. Currently defined macros: `CPPA1_ANT`, `CRPA1`.

**Request body:**
```json
{ "gpib_address": "GPIB0::3::INSTR" }
```

---

## Path Presets (`paths.json`)

Named relay configurations are persisted in `paths.json`. Each preset stores the target board and the active relay-to-path mapping:

```json
{
  "MyPath": {
    "board": "RSP-BRF",
    "relays": {
      "K31": "3",
      "K32": "1"
    }
  }
}
```

For SPDT relays, the value is `"NC"` or `"NO"`. For multi-path relays (SP6T/SP5T), the value is the path number as a string (e.g. `"3"`). Presets can be created, applied, and deleted directly from the GUI.

---

## Hardware Protocol Reference

For a full explanation of the `WD` command structure, register addressing, bit weight calculations, and per-module relay tables, see:

📄 [RF_Switching_Matrix_Control_Guide.md](RF_Switching_Matrix_Control_Guide.md)

### Command Syntax Quick Reference

```
WD <value> <register_address> <board_address>
```

| Field | Example | Description |
|---|---|---|
| `WD` | `WD` | Write Data opcode |
| `value` | `42` | Hex OR-sum of all active bits in the register |
| `register_address` | `95` | Target register address in hex (`90`–`95`) |
| `board_address` | `10` | TS-USM IEEE board address (default `10` hex) |

*Example:* `WD429510` — Sets K2 and K7 on the RSP-EMS board to C-NO, leaving all other REL1 relays unchanged.

---

## Project Structure

```
.
├── app.py                               # FastAPI REST API + GPIB hardware controller
├── gui.py                               # PySide6 desktop GUI
├── paths.json                           # Saved relay path presets
├── requirements.txt                     # Python dependencies
└── RF_Switching_Matrix_Control_Guide.md # Hardware protocol reference
```

---

## License

Distributed under the GPL-3.0 License. See [LICENSE](LICENSE) for details.
