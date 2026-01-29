import sys
import serial
import serial.tools.list_ports
from datetime import datetime
from skyfield.api import load, Topos
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel,
    QPushButton, QComboBox, QTextEdit, QLineEdit, QHBoxLayout, QCheckBox,
    QDateTimeEdit, QMessageBox
)
from PyQt6.QtCore import QTimer, Qt, QDateTime
print(load('de421.bsp'))

class AstroControl(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AstroControl Pro - v2.3")

        # === Skyfield ===
        self.ts = load.timescale()
        self.planets = load('de421.bsp')
        self.earth = self.planets['earth']

        # === Localização ===
        self.latitude = -23.55
        self.longitude = -46.63
        self.altitude = 760

        # === Tempo ===
        self.use_manual_time = False

        # === Estado ===
        self.tel_az = 0.0
        self.tel_alt = 0.0
        self.moving = False
        self.tracking = False

        # === Serial ===
        self.ser = None
        self.bt_status = False

        self.init_ui()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_display)
        self.timer.start(1000)

        # === Timer de TRACK ===
        self.track_timer = QTimer()
        self.track_timer.timeout.connect(self.track_target)

        # === Timer de leitura da Serial ===
        self.serial_timer = QTimer()
        self.serial_timer.timeout.connect(self.read_serial)
        self.serial_timer.start(100)

    # ================= UI =================
    def init_ui(self):
        layout = QVBoxLayout()

        # === Bluetooth ===
        layout.addWidget(QLabel("Bluetooth / Arduino"))

        bt_layout = QHBoxLayout()
        self.bt_combo = QComboBox()
        self.btn_scan_bt = QPushButton("Atualizar")
        self.btn_connect_bt = QPushButton("Conectar")

        self.btn_scan_bt.clicked.connect(self.scan_bt_devices)
        self.btn_connect_bt.clicked.connect(self.connect_bt)

        bt_layout.addWidget(self.bt_combo)
        bt_layout.addWidget(self.btn_scan_bt)
        bt_layout.addWidget(self.btn_connect_bt)
        layout.addLayout(bt_layout)

        self.scan_bt_devices()

        # === Astro ===
        layout.addWidget(QLabel("Alvo Astronômico"))
        self.astro_selector = QComboBox()
        self.astro_selector.addItems(
            ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter Barycenter", "Saturn Barycenter"]
        )
        layout.addWidget(self.astro_selector)

        # === Status ===
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # === Localização ===
        layout.addWidget(QLabel("Localização"))

        loc = QHBoxLayout()
        self.lat_input = QLineEdit(str(self.latitude))
        self.lon_input = QLineEdit(str(self.longitude))
        self.alt_input = QLineEdit(str(self.altitude))
        loc.addWidget(self.lat_input)
        loc.addWidget(self.lon_input)
        loc.addWidget(self.alt_input)
        layout.addLayout(loc)

        btn_loc = QPushButton("Aplicar localização manual")
        btn_loc.clicked.connect(self.apply_manual_location)
        layout.addWidget(btn_loc)

        # === Tempo ===
        self.manual_time_check = QCheckBox("Usar data/hora manual")
        self.manual_time_check.stateChanged.connect(self.toggle_manual_time)
        layout.addWidget(self.manual_time_check)

        self.datetime_edit = QDateTimeEdit(QDateTime.currentDateTime())
        self.datetime_edit.setDisplayFormat("dd/MM/yyyy HH:mm:ss")
        self.datetime_edit.setEnabled(False)
        layout.addWidget(self.datetime_edit)

        # === Coordenadas ===
        self.coord_label = QLabel("AZ: 0.00° | ALT: 0.00°")
        self.coord_label.setStyleSheet("font-size:18px;font-weight:bold")
        layout.addWidget(self.coord_label)

        self.tel_label = QLabel("TEL → AZ: 0.00° | ALT: 0.00°")
        layout.addWidget(self.tel_label)

        # === Log ===
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)

        # === Botões ===
        self.btn_goto = QPushButton("GOTO")
        self.btn_goto.clicked.connect(self.send_goto)
        layout.addWidget(self.btn_goto)

        self.btn_track = QPushButton("TRACK OFF")
        self.btn_track.clicked.connect(self.toggle_track)
        layout.addWidget(self.btn_track)

        btn_zero = QPushButton("Definir ZERO")
        btn_zero.clicked.connect(self.sync_zero)
        layout.addWidget(btn_zero)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        self.update_status()

    # ================= Bluetooth =================
    def scan_bt_devices(self):
        self.bt_combo.clear()
        for p in serial.tools.list_ports.comports():
            self.bt_combo.addItem(p.device)

    def connect_bt(self):
        try:
            self.ser = serial.Serial(self.bt_combo.currentText(), 9600, timeout=1)
            self.bt_status = True
            self.log_msg("🟢 Bluetooth conectado")
        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))
            self.bt_status = False
        self.update_status()

    def read_serial(self):
      if not self.ser:
          return

      try:
          while self.ser.in_waiting:
              line = self.ser.readline().decode(errors='ignore').strip()
              if line:
                  self.log_msg(f"📡 Arduino → {line}")
      except Exception as e:
          self.log_msg(f"🔴 Serial erro: {e}")

    # ================= Astronomia =================
    def get_time(self):
        if self.use_manual_time:
            return self.ts.from_datetime(
                self.datetime_edit.dateTime().toPyDateTime()
            )
        return self.ts.now()

    def get_az_alt(self):
        loc = self.earth + Topos(
            latitude_degrees=self.latitude,
            longitude_degrees=self.longitude,
            elevation_m=self.altitude
        )
        body = self.planets[self.astro_selector.currentText().lower()]
        alt, az, _ = loc.at(self.get_time()).observe(body).apparent().altaz()
        return az.degrees, alt.degrees

    # ================= Ações =================
    def send_goto(self):
        az, alt = self.get_az_alt()
        if alt < 0:
            self.log_msg("🔴 Alvo abaixo do horizonte")
            return

        cmd = f"GOTO AZ={az:.2f} ALT={alt:.2f}\n"
        if self.ser:
            self.ser.write(cmd.encode())

        self.tel_az = az
        self.tel_alt = alt
        self.log_msg(f"🟡 {cmd.strip()}")

    def toggle_track(self):
        self.tracking = not self.tracking

        if self.tracking:
            self.track_timer.start(2000)
            self.btn_track.setText("TRACK ON")
            self.log_msg("🟢 TRACK ativado")
        else:
            self.track_timer.stop()

            if self.ser:
                self.ser.write(b"STOP\n")

            self.btn_track.setText("TRACK OFF")
            self.log_msg("🛑 TRACK desativado")

        self.update_status()

    def track_target(self):
      if not self.ser or not self.tracking:
          return

      az, alt = self.get_az_alt()

      # Limitar abaixo do horizonte
      if alt < 0:
          self.log_msg("🔴 Alvo abaixo do horizonte (TRACK ignorado)")
          return

      # Envia comando TRACK somente se o alvo mudou significativamente
      delta_az = az - self.tel_az
      delta_alt = alt - self.tel_alt
      if abs(delta_az) < 0.05 and abs(delta_alt) < 0.05:
          return  # muito pequeno, ignora

      cmd = f"TRACK AZ={az:.2f} ALT={alt:.2f}\n"
      try:
          self.ser.write(cmd.encode())
          self.tel_az = az
          self.tel_alt = alt
          self.log_msg(f"🟡 {cmd.strip()}")
      except Exception as e:
          self.log_msg(f"🔴 Erro ao enviar TRACK: {e}")

    def sync_zero(self):
        self.tel_az = 0
        self.tel_alt = 0
        if self.ser:
            self.ser.write(b"ZERO\n")  # envia comando para Arduino
        self.log_msg("ZERO definido")

    def apply_manual_location(self):
        try:
            self.latitude = float(self.lat_input.text())
            self.longitude = float(self.lon_input.text())
            self.altitude = float(self.alt_input.text())
            self.log_msg("📍 Localização aplicada")
        except:
            self.log_msg("Erro de localização")

    def toggle_manual_time(self, s):
        self.use_manual_time = s == Qt.CheckState.Checked
        self.datetime_edit.setEnabled(self.use_manual_time)

    # ================= Atualização =================
    def update_display(self):
        az, alt = self.get_az_alt()
        self.coord_label.setText(f"AZ: {az:.2f}° | ALT: {alt:.2f}°")
        self.tel_label.setText(f"TEL → AZ: {self.tel_az:.2f}° | ALT: {self.tel_alt:.2f}°")

    def update_status(self):
        bt = "🟢 BT" if self.bt_status else "🔴 BT"
        tr = "🟡 TRACK" if self.tracking else "⚪ TRACK"
        self.status_label.setText(f"{bt} | {tr}")

    def log_msg(self, msg):
        self.log.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = AstroControl()
    w.show()
    sys.exit(app.exec())
