import sys
import requests
from PyQt6.QtWidgets import QApplication, QFileDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, QTimer

from qfluentwidgets import (FluentWindow, SubtitleLabel, PrimaryPushButton, 
                            InfoBar, InfoBarPosition, Theme, setTheme)
from qfluentwidgets import FluentIcon as FIF

class AttendanceTotem(FluentWindow):
    def __init__(self) -> None:
        super().__init__()
        self.SESSION_URL = "http://127.0.0.1:5001/api/active_session"
        self.DETECT_URL = "http://127.0.0.1:5002/detect"
        self.setWindowTitle("ITS Totem - Terminale Presenze")
        self.resize(600, 750) 
        self.navigationInterface.hide() 
        self.hBoxLayout.setContentsMargins(0, 0, 0, 0)
        self._setup_ui()
        setTheme(Theme.LIGHT)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_cloud_status)
        self.timer.start(3000)

    def _setup_ui(self):
        self.central_widget = QWidget()
        self.central_widget.setObjectName("totemInterface") 
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(50, 40, 50, 40)
        self.layout.setSpacing(10)

        # --- 1. RIGA 1: STATO E DOCENTE ---
        self.status_container = QWidget()
        self.status_layout = QHBoxLayout(self.status_container)
        self.status_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_dot = QLabel()
        self.status_dot.setFixedSize(12, 12)
        self.status_dot.setStyleSheet("background-color: #95a5a6; border-radius: 6px;")
        self.status_text = SubtitleLabel("CONNESSIONE IN CORSO...")
        self.status_text.setStyleSheet("font-weight: 800; font-size: 20px; margin-left: 10px;")
        self.status_layout.addWidget(self.status_dot)
        self.status_layout.addWidget(self.status_text)
        self.layout.addWidget(self.status_container)

        # --- 2. RIGA 2: INFO COMPATTE ---
        self.combined_info = SubtitleLabel("")
        self.combined_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.combined_info.setStyleSheet("color: #475569; font-weight: 500; font-size: 15px;")
        self.layout.addWidget(self.combined_info)
        self.layout.addSpacing(10)

        # --- 3. AREA CAMERA ---
        self.image_label = SubtitleLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumHeight(400)
        self.layout.addWidget(self.image_label)

        # --- 4. MESSAGGIO RISULTATO ---
        self.msg_box = SubtitleLabel("")
        self.msg_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.msg_box.setStyleSheet("font-weight: 600; color: #1e293b; height: 30px;")
        self.layout.addWidget(self.msg_box)

        # --- 5. PULSANTE ---
        self.btn_scan = PrimaryPushButton(FIF.PEOPLE, "Scansione Facciale")
        self.btn_scan.setFixedWidth(300)
        self.btn_scan.setFixedHeight(60)
        self.btn_scan.clicked.connect(self.run_detection)
        self.layout.addWidget(self.btn_scan, 0, Qt.AlignmentFlag.AlignCenter)
        self.set_camera_placeholder()
        self.addSubInterface(self.central_widget, FIF.HOME, 'Totem')

    def set_camera_placeholder(self):
        """Ripristina la grafica di attesa con icona e testo formattato"""
        self.image_label.setPixmap(QPixmap())
        
        # HTML per simulare òa grafica
        placeholder_html = """
            <div style='text-align: center;'>
                <p style='font-size: 60px; margin-bottom: 20px;'>📷</p>
                <p style='font-size: 18px; font-weight: 800; color: #1e293b; margin-bottom: 5px;'>INQUADRARE IL VOLTO</p>
                <p style='font-size: 13px; color: #64748b; font-weight: 400;'>pronto per la scansione</p>
            </div>
        """
        self.image_label.setText(placeholder_html)
        
        self.image_label.setStyleSheet("""
            border: 2px dashed #cbd5e1; 
            border-radius: 28px; 
            background: #f8fafc;
        """)
        self.msg_box.setText("")

    def check_cloud_status(self):
        try:
            res = requests.get(self.SESSION_URL, timeout=1.5)
            if res.status_code == 200:
                data = res.json()
                if data.get("active"):
                    self.status_dot.setStyleSheet("background-color: #2ecc71; border-radius: 6px;")
                    self.status_text.setText(f"PRONTO - {data['teacher_display'].upper()}")
                    self.combined_info.setText(f"{data['subject']} - {data['description']} - {data['range']}")
                    self.btn_scan.setEnabled(True)
                else:
                    self.status_dot.setStyleSheet("background-color: #e74c3c; border-radius: 6px;")
                    self.status_text.setText("IN ATTESA DI ATTIVAZIONE...")
                    self.combined_info.setText("Sessione non attiva dalla Dashboard")
                    self.btn_scan.setEnabled(False)
        except Exception:
            self.status_text.setText("⚠️ ERRORE CLOUD")
            self.status_dot.setStyleSheet("background-color: #95a5a6; border-radius: 6px;")

    def run_detection(self):
        path, _ = QFileDialog.getOpenFileName(self, "Simula Camera", "", "Images (*.jpg *.png)")
        if not path: return
        
        pixmap = QPixmap(path)
        self.image_label.setPixmap(pixmap.scaled(self.image_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.image_label.setText("")
        self.image_label.setStyleSheet("border: 2px solid #4f46e5; border-radius: 28px; background: #000;")

        try:
            with open(path, 'rb') as f:
                res = requests.post(self.DETECT_URL, files={'image': f}, timeout=5)
                data = res.json()
                if res.status_code == 200:
                    self.msg_box.setText(f"{data['status']}: {data['student_name']}")
                    InfoBar.success(title="Rilevato", content=data['message'], orient=Qt.Orientation.Horizontal, 
                                    isClosable=True, duration=3000, position=InfoBarPosition.TOP, parent=self)
                else:
                    self.msg_box.setText("ACCESSO NEGATO")
                    InfoBar.error(title="Errore", content=data['message'], orient=Qt.Orientation.Horizontal, 
                                  isClosable=True, duration=3000, position=InfoBarPosition.TOP, parent=self)            
            QTimer.singleShot(5000, self.set_camera_placeholder)
        except Exception:
            InfoBar.warning(title="Offline", content="Server non raggiungibile", orient=Qt.Orientation.Horizontal, 
                            isClosable=True, duration=3000, position=InfoBarPosition.TOP, parent=self)
            QTimer.singleShot(2000, self.set_camera_placeholder)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AttendanceTotem()
    window.show()
    sys.exit(app.exec())