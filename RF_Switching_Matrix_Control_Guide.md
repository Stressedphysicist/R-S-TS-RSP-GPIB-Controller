# RF Switching Matrix: TS-RSP Remote Control Guide

## 1. System Operations & Architectural Logic
The remote control architecture for the RF Switching Matrix relies on the TS-USM I/O board. Control over individual relays across multiple plug-in modules is achieved by manipulating the state of specific 8-bit data registers. The system allocates individual bits within these registers to specific relay states. 

**Critical Hardware Constraint:** The TS-USM board does not support reading back the current content of these registers. Therefore, the control application software must initialize, track, and buffer the state of all relays locally. To maintain the state of untouched relays when switching a single relay, the entire updated 8-bit state must be sent in a new command for that specific register.

### 1.1 Register Mapping
The system utilizes 6 specific data registers:
*   **Open Collector Drivers (4 registers):** OC0, OC1, OC2, OC3
*   **High Side Drivers (2 registers):** REL0, REL1

### 1.2 Command Syntax
Commands sent to the interface follow a strict structure:
**`WD<register><register address><board address>`**

*   **`WD`**: Write Data command initialization.
*   **`<register>`**: The new value (in Hexadecimal) to be written into the register. This value is the mathematical sum of all currently set bits.
*   **`<register address>`**: The specific Hex address of the targeted register.
*   **`<board address>`**: The IEEE address of the TS-USM board (Default is `10` hex).

### 1.3 Hexadecimal Bit Calculation
To calculate the `<register>` Hex value, apply the following summation based on the required active bits:
$Val_{decimal} = \sum_{n=1}^{8} a * 2^{n-1}$ (where $a=1$ if the bit is set, and $0$ if not set).

| Bit Number | Decimal Weight | Hexadecimal Value |
| :--- | :--- | :--- |
| Bit 1 | 1 | **01** |
| Bit 2 | 2 | **02** |
| Bit 3 | 4 | **04** |
| Bit 4 | 8 | **08** |
| Bit 5 | 16 | **10** |
| Bit 6 | 32 | **20** |
| Bit 7 | 64 | **40** |
| Bit 8 | 128 | **80** |

*Example:* To set Bit 2 (02hex) and Bit 7 (40hex) simultaneously, the register value sent is `42`.

---

## 2. Global Initialization Sequence
At the start of the control application, the TS-USM board must be forced into a defined, clean state. The following sequence zeroes out all operational registers:

| Command | Action |
| :--- | :--- |
| `WD009010` | Clears output register OC0 (Address 90hex) |
| `WD009110` | Clears output register OC1 (Address 91hex) |
| `WD009210` | Clears output register OC2 (Address 92hex) |
| `WD009310` | Clears output register OC3 (Address 93hex) |
| `WD009410` | Clears output register REL0 (Address 94hex) |
| `WD009510` | Clears output register REL1 (Address 95hex) |

---

## 3. Plug-in Module Configurations

### 3.1 RSP-EMS Plug-in
Controls two-path relays (SPDT). One output line is required per relay. 
*   **C-NC (Normally Closed):** Bit is NOT set (0).
*   **C-NO (Normally Open):** Bit is SET (1).

| Relay | Register | Register Address | Bit No. | Hex Value |
| :--- | :--- | :--- | :--- | :--- |
| **K1** | REL1 | 95hex | 1 | 01hex |
| **K2** | REL1 | 95hex | 2 | 02hex |
| **K3** | REL1 | 95hex | 3 | 04hex |
| **K4** | REL1 | 95hex | 4 | 08hex |
| **K5** | REL1 | 95hex | 5 | 10hex |
| **K6** | REL1 | 95hex | 6 | 20hex |
| **K7** | REL1 | 95hex | 7 | 40hex |
| **K10** | REL0 | 94hex | 1 | 01hex |
| **K11** | REL0 | 94hex | 2 | 02hex |
| **K12** | REL0 | 94hex | 3 | 04hex |
| **K13** | REL0 | 94hex | 4 | 08hex |

*Example Command:* `WD429510` (Sets K2 and K7 on the EMS board to C-NO, keeping all other REL1 relays at C-NC).

### 3.2 RSP-EMI Plug-in
Controls two-path relays (SPDT) distributed across multiple registers.

| Relay | Register | Register Address | Bit No. | Hex Value |
| :--- | :--- | :--- | :--- | :--- |
| **K20** | OC2 | 92hex | 5 | 10hex |
| **K21** | OC2 | 92hex | 6 | 20hex |
| **K24** | OC3 | 93hex | 1 | 01hex |
| **K25** | OC3 | 93hex | 2 | 02hex |
| **K22** | REL0 | 94hex | 7 | 40hex |
| **K23** | REL0 | 94hex | 8 | 80hex |

### 3.3 RSP-BRF Plug-in
**CRITICAL LOGIC WARNING:** The BRF board uses multi-path relays (SP6T). Consequently, **only ONE line of the relay control input must be set at any given time** to prevent hardware conflict.

| Relay | Register | Address | Path 1 (01hex) | Path 2 (02hex) | Path 3 (04hex) | Path 4 (08hex) | Path 5 (10hex) | Path 6 (20hex) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **K31** | OC3 | 93hex | C -> 1 *(04hex)* | C -> 2 *(08hex)* | C -> 3 *(10hex)* | C -> 4 *(20hex)* | C -> 5 *(40hex)* | C -> 6 *(80hex)* |
| **K32** | OC2 | 92hex | C -> 1 *(01hex)* | C -> 2 *(02hex)* | C -> 3 *(04hex)* | C -> 4 *(08hex)* | C -> 5 *(40hex)* | C -> 6 *(80hex)* |
| **K33** | REL0 | 94hex | C -> 1 *(01hex)* | C -> 2 *(02hex)* | C -> 3 *(04hex)* | C -> 4 *(08hex)* | C -> 5 *(10hex)* | C -> 6 *(20hex)* |
| **K34** | REL1 | 95hex | C -> 1 *(01hex)* | C -> 2 *(02hex)* | C -> 3 *(04hex)* | C -> 4 *(08hex)* | C -> 5 *(10hex)* | C -> 6 *(20hex)* |

*(Note: K31 and K32 have non-standard bit alignments for their paths. Refer strictly to the Hex values provided in the cell).*

### 3.4 RSP-MMF Plug-in
**CRITICAL LOGIC WARNING:** The MMF board also utilizes multi-path relays. Always ensure only a single line is set per relay.

| Relay | Register | Address | Path 1 (01hex) | Path 2 (02hex) | Path 3 (04hex) | Path 4 (08hex) | Path 5 (10hex) | Path 6 (20hex) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **K21** | OC3 | 93hex | C -> 1 *(04hex)* | C -> 2 *(08hex)* | C -> 3 *(10hex)* | C -> 4 *(20hex)* | C -> 5 *(40hex)* | C -> 6 *(80hex)* |
| **K22** | OC2 | 92hex | C -> 1 *(01hex)* | C -> 2 *(02hex)* | C -> 3 *(04hex)* | C -> 4 *(08hex)* | C -> 5 *(40hex)* | C -> 6 *(80hex)* |
| **K23** | REL0 | 94hex | C -> 1 *(01hex)* | C -> 2 *(02hex)* | C -> 3 *(04hex)* | C -> 4 *(08hex)* | C -> 5 *(10hex)* | N/A |
| **K24** | REL1 | 95hex | C -> 1 *(01hex)* | C -> 2 *(02hex)* | C -> 3 *(04hex)* | C -> 4 *(08hex)* | C -> 5 *(10hex)* | N/A |

### 3.5 RSP-MMS Plug-in
Standard two-path (SPDT) relays distributed across multiple driver registers.

| Relay | Register | Register Address | Bit No. | Hex Value |
| :--- | :--- | :--- | :--- | :--- |
| **K1** | OC2 | 92hex | 5 | 10hex |
| **K2** | OC2 | 92hex | 6 | 20hex |
| **K3** | OC3 | 93hex | 1 | 01hex |
| **K4** | OC3 | 93hex | 2 | 02hex |
| **K5** | REL0 | 94hex | 8 | 80hex |
| **K7** | REL0 | 94hex | 6 | 20hex |
| **K8** | REL0 | 94hex | 7 | 40hex |
| **K6** | REL1 | 95hex | 6 | 20hex |
| **K9** | REL1 | 95hex | 7 | 40hex |
| **K10** | REL1 | 95hex | 8 | 80hex |
