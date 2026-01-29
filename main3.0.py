# SOFTWATE PARA CONTROLE DE TELESCOPIO (LAT360/ALT90) COM MOTOR DE PASSO NEMA (RECOMENDADO) 17 EM ARDUINO UNO
# VERSAO 3.0 STABLE DESENVOLVIDA POR BRYAM S. SIERPINSKI EM 01/2026
# Utiliza biblioteca Skyfiel de421.bsd para calculos trigonometricos. Produzido pelo Jet Propulsion Laboratory (JPL) da NASA. Ele fornece dados de efemérides (posições e velocidades) precisos para o Sol, a Lua, planetas e os principais satélites do sistema solar, cobrindo o período de 1900 a 2050. 
# USO LIVRE :)

import sys
import os
import time
import serial
import serial.tools.list_ports
from datetime import datetime
from skyfield.api import load, Topos
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel,
    QPushButton, QComboBox, QTextEdit, QLineEdit, QHBoxLayout, QCheckBox,
    QDateTimeEdit
)
from PyQt6.QtCore import QTimer, Qt, QDateTime, QThread, pyqtSignal

class SerialWorker(QThread):
    data_received = pyqtSignal(str)
    status = pyqtSignal(bool, str)

    def __init__(self, port, baud=9600):
        super().__init__()
        self.port = port
        self.baud = baud
        self.running = True
        self.serial_thread = None

    def run(self):
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=0.1)
            self.status.emit(True, "🟢 Serial conectada")

            buffer = b""

            while self.running:
                if self.ser.in_waiting:
                    data = self.ser.read(self.ser.in_waiting)
                    buffer += data

                    #Apenas linhas ASCII
                    while b'\n' in buffer:
                        line, buffer = buffer.split(b'\n', 1)
                        try:
                            text = line.decode('ascii').strip()
                            if text:
                                self.data_received.emit(text)
                        except UnicodeDecodeError:
                            # ignora binario por enquanto
                            pass

                time.sleep(0.01)

        except Exception as e:
            self.status.emit(False, f"🔴 Serial erro: {e}")

    def send(self, data: str):
        if self.ser and self.ser.is_open:
            self.ser.write(data.encode())

    def stop(self):
        self.running = False
        if self.ser:
            self.ser.close()
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class AstroControl(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AstroControl Pro - v3.0")

        # === Skyfield ===
        self.ts = load.timescale()
        self.planets = load(resource_path('de421.bsp')) 
        self.earth = self.planets['earth']

        # === Localização ===
        self.latitude = -26.259963
        self.longitude = -52.675883
        self.altitude = 800

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
        self.serial_thread = None

        self.init_ui()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_display)
        self.timer.start(1000)

        # === Timer de TRACK ===
        self.track_timer = QTimer()
        self.track_timer.timeout.connect(self.track_target)

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

        # === Atmosfera ===
        layout.addWidget(QLabel("Atmosfera (Refração)"))

        atm = QHBoxLayout()
        self.temp_input = QLineEdit("10")       # Temp em °C
        self.press_input = QLineEdit("1013")    # Pressao atmosferia em mbar (precisa converter de atm)

        self.temp_input.setPlaceholderText("Temp (°C)")
        self.press_input.setPlaceholderText("Pressão (mbar)")

        atm.addWidget(self.temp_input)
        atm.addWidget(self.press_input)
        layout.addLayout(atm)

        self.use_refraction = QCheckBox("Usar refração atmosférica")
        self.use_refraction.setChecked(True)
        layout.addWidget(self.use_refraction)

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
        port = self.bt_combo.currentText()

        self.serial_thread = SerialWorker(port)
        self.serial_thread.data_received.connect(self.on_serial_data)
        self.serial_thread.status.connect(self.on_serial_status)

        self.serial_thread.start()

    def on_serial_data(self, line):
        self.log_msg(f"📡 Arduino → {line}")

    def on_serial_status(self, ok, msg):
        self.bt_status = ok
        self.log_msg(msg)
        self.update_status()

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
        astrometric = loc.at(self.get_time()).observe(body).apparent()

        temp, press = self.get_atmosphere()

        if temp is not None and press is not None:
            alt, az, _ = astrometric.altaz(
                temperature_C=temp,
                pressure_mbar=press
            )
        else:
            alt, az, _ = astrometric.altaz()

        return az.degrees, alt.degrees
    
    def get_atmosphere(self):
        if not self.use_refraction.isChecked():
            return None, None

        try:
            temp = float(self.temp_input.text())
            press = float(self.press_input.text())
            return temp, press
        except:
            self.log_msg("⚠️ Dados atmosfericos inválida, usando Skyfiel sem correção do horizonte baixo")
            return None, None

    # ================= Ações =================
    def send_goto(self):
        az, alt = self.get_az_alt()
        if alt < -0.5:
            self.log_msg("🔴 Alvo abaixo do horizonte (refração ignorada)")
            return

        # Calcular menor delta para azimute
        delta_az = (az - self.tel_az + 180) % 360 - 180
        final_az = self.tel_az + delta_az

        cmd = f"GOTO AZ={final_az:.2f} ALT={alt:.2f}\n"
        if self.serial_thread:
            self.serial_thread.send(cmd)

        self.tel_az = az
        self.tel_alt = alt
        self.log_msg(f"🟡 {cmd.strip()}")

    def toggle_track(self):
        self.tracking = not self.tracking

        if self.tracking:
            self.track_timer.start(100)
            self.btn_track.setText("TRACK ON")
            self.log_msg("🟢 TRACK ativado")
        else:
            self.track_timer.stop()

            if self.serial_thread:
                self.serial_thread.send("STOP\n")

            self.btn_track.setText("TRACK OFF")
            self.log_msg("🛑 TRACK desativado")

        self.update_status()

    def track_target(self):
        if not self.serial_thread or not self.tracking:
            return

        now = datetime.utcnow().timestamp()
        az, alt = self.get_az_alt()

        if not hasattr(self, "last_track_time"):
            self.last_track_time = now
            self.last_az = az
            self.last_alt = alt
            return

        if alt < 1.0:
            return
        
        dt = now - self.last_track_time
        if dt <= 0:
            return

        # velocidade angular (graus por segundo)
        vaz = (az - self.last_az) / dt
        valt = (alt - self.last_alt) / dt

        # ignora micro ruido ou microvariações para nao sobrecarregar
        if abs(vaz) < 0.0001 and abs(valt) < 0.0001:
            return

        cmd = f"TRACK VAZ={vaz:.6f} VALT={valt:.6f}\n"
        self.send_track_binary(vaz, valt)

        self.last_track_time = now
        self.last_az = az
        self.last_alt = alt

    def sync_zero(self):
        self.tel_az = 0
        self.tel_alt = 0
        if self.serial_thread:
            self.serial_thread.send("ZERO\n")
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

    def closeEvent(self, event):
        if self.serial_thread:
            self.serial_thread.stop()
            self.serial_thread.wait()
        event.accept()

    def send_track_binary(self, vaz, valt):
        # converte °/s → milideg/s
        vaz_i = int(vaz * 1000)
        valt_i = int(valt * 1000)

        payload = (
            b'\x02' +
            b'T' +
            vaz_i.to_bytes(4, 'little', signed=True) +
            valt_i.to_bytes(4, 'little', signed=True)
        )

        chk = sum(payload[1:]) & 0xFF
        frame = payload + bytes([chk]) + b'\x03'

        self.serial_thread.ser.write(frame)

        self.log_msg(
            f"🟣 TRACK BIN → "
            f"VAZ={vaz:+.6f} °/s | "
            f"VALT={valt:+.6f} °/s"
        )

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = AstroControl()
    w.show()
    sys.exit(app.exec())

#PS: Não sou programador Python e nem astronomo, só cuiroso...
#Caso tenha alguma ideia, fique a vontade para contribuir.