import sys
import json
import os
import requests
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QRadioButton, QCheckBox, QPushButton, QLabel, 
    QLineEdit, QFrame, QButtonGroup, QSpacerItem, QSizePolicy, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt

API_BASE_URL = "http://localhost:8001"
GPIB_ADDRESS = "GPIB0::3::INSTR"
PATHS_FILE = "paths.json"

# --- Hardware Configuration Dictionary ---
BOARD_CONFIGS = {
    "RSP-EMS": {
        "K1": {"type": "SPDT", "reg": "0x95", "bit": "0x01"},
        "K2": {"type": "SPDT", "reg": "0x95", "bit": "0x02"},
        "K3": {"type": "SPDT", "reg": "0x95", "bit": "0x04"},
        "K4": {"type": "SPDT", "reg": "0x95", "bit": "0x08"},
        "K5": {"type": "SPDT", "reg": "0x95", "bit": "0x10"},
        "K6": {"type": "SPDT", "reg": "0x95", "bit": "0x20"},
        "K7": {"type": "SPDT", "reg": "0x95", "bit": "0x40"},
        "K10": {"type": "SPDT", "reg": "0x94", "bit": "0x01"},
        "K11": {"type": "SPDT", "reg": "0x94", "bit": "0x02"},
        "K12": {"type": "SPDT", "reg": "0x94", "bit": "0x04"},
        "K13": {"type": "SPDT", "reg": "0x94", "bit": "0x08"},
    },
    "RSP-EMI": {
        "K20": {"type": "SPDT", "reg": "0x92", "bit": "0x10"},
        "K21": {"type": "SPDT", "reg": "0x92", "bit": "0x20"},
        "K24": {"type": "SPDT", "reg": "0x93", "bit": "0x01"},
        "K25": {"type": "SPDT", "reg": "0x93", "bit": "0x02"},
        "K22": {"type": "SPDT", "reg": "0x94", "bit": "0x40"},
        "K23": {"type": "SPDT", "reg": "0x94", "bit": "0x80"},
    },
    "RSP-BRF": {
        "K31": {"type": "SPNT", "reg": "0x93", "paths": {"1": "0x04", "2": "0x08", "3": "0x10", "4": "0x20", "5": "0x40", "6": "0x80"}},
        "K32": {"type": "SPNT", "reg": "0x92", "paths": {"1": "0x01", "2": "0x02", "3": "0x04", "4": "0x08", "5": "0x40", "6": "0x80"}},
        "K33": {"type": "SPNT", "reg": "0x94", "paths": {"1": "0x01", "2": "0x02", "3": "0x04", "4": "0x08", "5": "0x10", "6": "0x20"}},
        "K34": {"type": "SPNT", "reg": "0x95", "paths": {"1": "0x01", "2": "0x02", "3": "0x04", "4": "0x08", "5": "0x10", "6": "0x20"}},
    },
    "RSP-MMF": {
        "K21": {"type": "SPNT", "reg": "0x93", "paths": {"1": "0x04", "2": "0x08", "3": "0x10", "4": "0x20", "5": "0x40", "6": "0x80"}},
        "K22": {"type": "SPNT", "reg": "0x92", "paths": {"1": "0x01", "2": "0x02", "3": "0x04", "4": "0x08", "5": "0x40", "6": "0x80"}},
        "K23": {"type": "SPNT", "reg": "0x94", "paths": {"1": "0x01", "2": "0x02", "3": "0x04", "4": "0x08", "5": "0x10"}},
        "K24": {"type": "SPNT", "reg": "0x95", "paths": {"1": "0x01", "2": "0x02", "3": "0x04", "4": "0x08", "5": "0x10"}},
    },
    "RSP-MMS": {
        "K1": {"type": "SPDT", "reg": "0x92", "bit": "0x10"},
        "K2": {"type": "SPDT", "reg": "0x92", "bit": "0x20"},
        "K3": {"type": "SPDT", "reg": "0x93", "bit": "0x01"},
        "K4": {"type": "SPDT", "reg": "0x93", "bit": "0x02"},
        "K7": {"type": "SPDT", "reg": "0x94", "bit": "0x20"},
        "K8": {"type": "SPDT", "reg": "0x94", "bit": "0x40"},
        "K5": {"type": "SPDT", "reg": "0x94", "bit": "0x80"},
        "K6": {"type": "SPDT", "reg": "0x95", "bit": "0x20"},
        "K9": {"type": "SPDT", "reg": "0x95", "bit": "0x40"},
        "K10": {"type": "SPDT", "reg": "0x95", "bit": "0x80"},
    }
}

class RelayBox(QFrame):
    """Dynamically generates the relay control block based on board config."""
    def __init__(self, relay_name, config, callback):
        super().__init__()
        self.relay_name = relay_name
        self.config = config
        self.callback = callback 
        self.is_updating = False 
        
        self.setFrameStyle(QFrame.Panel | QFrame.Raised)
        self.setLineWidth(2)
        
        layout = QVBoxLayout()
        layout.setSpacing(2)
        layout.setContentsMargins(5, 5, 5, 5)

        self.enable_checkbox = QCheckBox(relay_name)
        self.enable_checkbox.toggled.connect(self.on_interaction)
        layout.addWidget(self.enable_checkbox)

        self.radio_group = QButtonGroup(self)
        self.radio_group.buttonClicked.connect(self.on_interaction)
        
        radio_layout = QGridLayout()
        self.radios = {}
        
        # Options logic based on SPDT vs Multi-path SPNT
        options = ["NC", "NO"] if config["type"] == "SPDT" else list(config["paths"].keys())
        
        for i, opt in enumerate(options):
            rb = QRadioButton(opt)
            if i == 0: rb.setChecked(True)
            self.radio_group.addButton(rb, i)
            self.radios[opt] = rb
            
            row = i // 2
            col = i % 2
            radio_layout.addWidget(rb, row, col, alignment=Qt.AlignCenter)

        layout.addLayout(radio_layout)
        self.setLayout(layout)
        self.toggle_ui_state(False)

    def toggle_ui_state(self, enabled):
        for rb in self.radios.values():
            rb.setEnabled(enabled)

    def on_interaction(self):
        if self.is_updating: return
        is_checked = self.enable_checkbox.isChecked()
        self.toggle_ui_state(is_checked)
        
        selected_option = self.radio_group.checkedButton().text()
        self.callback(self.relay_name, self.config, selected_option, is_checked)

    def set_state_silently(self, is_enabled, selected_option=None):
        self.is_updating = True
        self.enable_checkbox.setChecked(is_enabled)
        self.toggle_ui_state(is_enabled)
        if selected_option and selected_option in self.radios:
            self.radios[selected_option].setChecked(True)
        self.is_updating = False


class TS_RSP_Live_GUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Properties: TS-RSP Control Matrix")
        self.setStyleSheet("QWidget { background-color: #C0C0C0; } QGroupBox { font-weight: bold; }")
        
        self.current_board = "RSP-EMS"
        self.relay_widgets = {}
        self.saved_paths = self.load_paths_from_json()
        
        self.main_layout = QVBoxLayout(self)
        self.setup_paths_list()
        
        middle_layout = QHBoxLayout()
        self.setup_board_group(middle_layout)
        
        self.relay_group = QGroupBox("Relay Setting")
        self.relay_layout = QGridLayout()
        self.relay_group.setLayout(self.relay_layout)
        middle_layout.addWidget(self.relay_group)
        
        self.setup_action_buttons(middle_layout)
        self.main_layout.addLayout(middle_layout)
        
        self.setup_bottom_bar()
        self.draw_relay_grid() 
        self.refresh_paths_list()

    def setup_paths_list(self):
        self.paths_list = QListWidget()
        self.paths_list.setStyleSheet("background-color: white;")
        self.paths_list.itemClicked.connect(self.apply_path_macro)
        self.main_layout.addWidget(self.paths_list)

    def setup_board_group(self, parent_layout):
        group = QGroupBox("Relay Board")
        layout = QVBoxLayout()
        self.board_group = QButtonGroup(self)
        
        for i, board in enumerate(BOARD_CONFIGS.keys()):
            rb = QRadioButton(board)
            if i == 0: rb.setChecked(True)
            self.board_group.addButton(rb, i)
            layout.addWidget(rb)
            
        self.board_group.buttonClicked.connect(self.change_board)
        layout.addStretch()
        group.setLayout(layout)
        parent_layout.addWidget(group)

    def setup_action_buttons(self, parent_layout):
        layout = QVBoxLayout()
        
        btn_add = QPushButton("Add")
        btn_add.clicked.connect(self.save_current_path)
        
        btn_delete = QPushButton("Delete")
        btn_delete.clicked.connect(self.delete_selected_path)
        
        btn_clear = QPushButton("Clear")
        btn_clear.clicked.connect(self.clear_ui)
        
        layout.addWidget(btn_add)
        layout.addWidget(btn_delete)
        spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        layout.addItem(spacer)
        layout.addWidget(btn_clear)
        parent_layout.addLayout(layout)

    def setup_bottom_bar(self):
        layout = QHBoxLayout()
        layout.addWidget(QLabel("Path"))
        self.path_input = QLineEdit()
        self.path_input.setStyleSheet("background-color: white; border: 1px inset gray;") 
        layout.addWidget(self.path_input)
        self.main_layout.addLayout(layout)

    def draw_relay_grid(self):
        # Meticulous and safe deallocation of C++ widget pointers
        while self.relay_layout.count():
            item = self.relay_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
                
        self.relay_widgets.clear()

        config = BOARD_CONFIGS.get(self.current_board, {})
        
        row, col = 0, 0
        for name, relay_cfg in config.items():
            box = RelayBox(name, relay_cfg, self.live_api_call)
            self.relay_layout.addWidget(box, row, col)
            self.relay_widgets[name] = box
            
            col += 1
            if col > 3: 
                col = 0
                row += 1

    def change_board(self, button):
        self.current_board = button.text()
        self.draw_relay_grid()

    def live_api_call(self, relay_name, config, selected_option, is_enabled):
        print(f"LIVE ACTION: Board={self.current_board}, Relay={relay_name}, Option={selected_option}, Enabled={is_enabled}")
        
        if config["type"] == "SPDT":
            state_bool = True if is_enabled and selected_option == "NO" else False
            payload = {
                "gpib_address": GPIB_ADDRESS,
                "register": config["reg"],
                "bit_value": config["bit"],
                "state": state_bool
            }
            try:
                requests.post(f"{API_BASE_URL}/relay/set", json=payload)
            except Exception as e:
                print(f"API Error: {e}")
                
        elif config["type"] == "SPNT":
            try:
                # MANDATORY PROTOCOL: Clear all paths on this relay to prevent conflict
                for path, bit_val in config["paths"].items():
                    payload = {
                        "gpib_address": GPIB_ADDRESS,
                        "register": config["reg"],
                        "bit_value": bit_val,
                        "state": False
                    }
                    requests.post(f"{API_BASE_URL}/relay/set", json=payload)
                
                # Activate selected path strictly if enabled
                if is_enabled and selected_option in config["paths"]:
                    payload = {
                        "gpib_address": GPIB_ADDRESS,
                        "register": config["reg"],
                        "bit_value": config["paths"][selected_option],
                        "state": True
                    }
                    requests.post(f"{API_BASE_URL}/relay/set", json=payload)
            except Exception as e:
                print(f"API Error: {e}")

    def load_paths_from_json(self):
        if os.path.exists(PATHS_FILE):
            with open(PATHS_FILE, "r") as f:
                return json.load(f)
        return {}

    def save_paths_to_json(self):
        with open(PATHS_FILE, "w") as f:
            json.dump(self.saved_paths, f, indent=4)

    def refresh_paths_list(self):
        self.paths_list.clear()
        for path_name, data in self.saved_paths.items():
            settings_str = " ".join([f"{k}{v}" for k, v in data["relays"].items()])
            display_text = f"{path_name:<15} {data['board'].replace('RSP-', ''):<10} {settings_str}"
            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, path_name) 
            self.paths_list.addItem(item)

    def save_current_path(self):
        path_name = self.path_input.text().strip()
        if not path_name: return
        
        active_relays = {}
        for name, widget in self.relay_widgets.items():
            if widget.enable_checkbox.isChecked():
                active_relays[name] = widget.radio_group.checkedButton().text()
                
        self.saved_paths[path_name] = {
            "board": self.current_board,
            "relays": active_relays
        }
        self.save_paths_to_json()
        self.refresh_paths_list()
        print(f"System Update: Saved Path '{path_name}'")

    def apply_path_macro(self, item):
        path_name = item.data(Qt.UserRole)
        data = self.saved_paths.get(path_name)
        if not data: return
        
        self.path_input.setText(path_name)
        
        if data["board"] != self.current_board:
            for btn in self.board_group.buttons():
                if btn.text() == data["board"]:
                    btn.setChecked(True)
                    self.change_board(btn)
                    break
        
        print(f"--- Enacting Macro Path Protocol: {path_name} ---")
        for name, widget in self.relay_widgets.items():
            if name in data["relays"]:
                selected_opt = data["relays"][name]
                widget.set_state_silently(True, selected_opt)
                self.live_api_call(name, widget.config, selected_opt, True)
            else:
                widget.set_state_silently(False)
                default_opt = widget.radio_group.checkedButton().text()
                self.live_api_call(name, widget.config, default_opt, False)

    def delete_selected_path(self):
        item = self.paths_list.currentItem()
        if item:
            path_name = item.data(Qt.UserRole)
            if path_name in self.saved_paths:
                del self.saved_paths[path_name]
                self.save_paths_to_json()
                self.refresh_paths_list()

    def clear_ui(self):
        for widget in self.relay_widgets.values():
            widget.set_state_silently(False)
        self.path_input.clear()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Windows") 
    window = TS_RSP_Live_GUI()
    window.show()
    sys.exit(app.exec())