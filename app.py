import threading
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import pyvisa

app = FastAPI(title="Dynamic Rohde & Schwarz TS-RSP Controller API")

# --- Core Hardware Controller Logic ---
class TSRSP_Controller:
    def __init__(self, board_address=0x10):
        # Initialize rm to None to avoid import-time crashes if VISA is missing
        self.rm = None
        # board_address 0x10 (16) is the default hardware address for TS-RSP
        self.board_address = board_address
        
        # Dictionaries to track independent states and connections per GPIB address
        self.state_buffers = {}
        self.instruments = {}
        self.locks = {}

    def _get_lock(self, gpib_address: str):
        if gpib_address not in self.locks:
            self.locks[gpib_address] = threading.Lock()
        return self.locks[gpib_address]

    def _get_instrument(self, gpib_address: str):
        """Fetches or opens a VISA connection for a specific address."""
        if self.rm is None:
            self.rm = pyvisa.ResourceManager()

        if gpib_address not in self.instruments:
            try:
                self.instruments[gpib_address] = self.rm.open_resource(gpib_address)
            except Exception as e:
                print(f"WARNING: Failed to connect to {gpib_address}. Error: {e}")
                print(f"Operating in SIMULATION mode for {gpib_address}.")
                return None
        return self.instruments.get(gpib_address)

    def _get_registers(self, gpib_address: str):
        """Fetches or initializes the state buffer for a specific address."""
        if gpib_address not in self.state_buffers:
            # 90-93 = OC0-OC3, 94-95 = REL0-REL1
            self.state_buffers[gpib_address] = {
                0x90: 0x00, 0x91: 0x00, 0x92: 0x00, 
                0x93: 0x00, 0x94: 0x00, 0x95: 0x00
            }
        return self.state_buffers[gpib_address]

    def initialize_system(self, gpib_address: str):
        """Cleans all output registers to defined state 0x00 for a given address."""
        with self._get_lock(gpib_address):
            regs = self._get_registers(gpib_address)
            for reg in regs.keys():
                regs[reg] = 0x00
                self._write_register(gpib_address, reg)
            
    def _write_register(self, gpib_address: str, register_address: int):
        """Builds and sends the WD command."""
        regs = self._get_registers(gpib_address)
        value = regs[register_address]
        
        cmd = f"WD{value:02X}{register_address:02X}{self.board_address:02X}"
        inst = self._get_instrument(gpib_address)
        
        if inst:
            inst.write(cmd)
        print(f"[{gpib_address}] Executed: {cmd}")

    def set_relay(self, gpib_address: str, register_address: int, bit_hex_value: int, state: bool, clear_mask: int = 0):
        """Safely toggles bits using a discrete buffer per instrument."""
        with self._get_lock(gpib_address):
            regs = self._get_registers(gpib_address)
            current_val = regs[register_address]
            
            new_val = current_val
            
            # 1. Apply mutual exclusion mask first (Clear previous paths)
            if clear_mask:
                new_val &= (~clear_mask) & 0xFF
                
            # 2. Apply the specific target state
            if state:
                new_val |= bit_hex_value
            else:
                new_val &= (~bit_hex_value) & 0xFF
            
            if new_val != current_val:
                regs[register_address] = new_val
                self._write_register(gpib_address, register_address)

# Initialize the hardware controller singleton
matrix = TSRSP_Controller()


# --- Pydantic Schemas for API Requests ---
class BaseMatrixRequest(BaseModel):
    gpib_address: str

class RelayRequest(BaseMatrixRequest):
    register: str  
    bit_value: str 
    state: bool    
    clear_mask: Optional[str] = None


# --- API Endpoints ---
@app.get("/state")
def get_state(gpib_address: str):
    """Returns the current buffered state of all registers for a specific instrument via query parameter."""
    regs = matrix._get_registers(gpib_address)
    return {f"0x{k:02X}": f"0x{v:02X}" for k, v in regs.items()}

@app.post("/initialize")
def initialize(req: BaseMatrixRequest):
    """Resets all relay registers to 0x00 for the requested GPIB address."""
    matrix.initialize_system(req.gpib_address)
    return {"status": "success", "message": f"All registers cleared on {req.gpib_address}."}

@app.post("/relay/set")
def set_relay(req: RelayRequest):
    """Directly toggle an individual bit on a specific register."""
    print(f"\n[INCOMING REQUEST PAYLOAD] -> {req.model_dump_json(indent=2)}\n")

    try:
        reg_int = int(req.register, 16)
        bit_int = int(req.bit_value, 16)
        clear_int = int(req.clear_mask, 16) if req.clear_mask else 0
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Hex formatting. Use string format '0x95'.")

    # Validate register bounds
    if reg_int not in matrix._get_registers(req.gpib_address):
         raise HTTPException(status_code=400, detail="Invalid register address.")

    matrix.set_relay(req.gpib_address, reg_int, bit_int, req.state, clear_int)
    regs = matrix._get_registers(req.gpib_address)
    return {"status": "success", "gpib": req.gpib_address, "register": req.register, "new_value": f"0x{regs[reg_int]:02X}"}

@app.post("/path/switch/{path_name}")
def switch_macro_path(path_name: str, req: BaseMatrixRequest):
    """Mimics macro paths for a specific GPIB instrument."""
    path = path_name.upper()
    addr = req.gpib_address
    
    if path == "CPPA1_ANT":
        matrix.set_relay(addr, 0x94, 0x02, True)
        matrix.set_relay(addr, 0x94, 0x04, True)
        return {"status": "success", "gpib": addr, "path": path, "active_relays": ["K11_1", "K12_1"]}
        
    elif path == "CRPA1":
        matrix.set_relay(addr, 0x95, 0x10, True)
        matrix.set_relay(addr, 0x95, 0x20, True)
        matrix.set_relay(addr, 0x95, 0x40, True)
        return {"status": "success", "gpib": addr, "path": path, "active_relays": ["K5NO", "K6NO", "K7NO"]}
        
    else:
        raise HTTPException(status_code=404, detail=f"Path macro '{path_name}' not defined.")