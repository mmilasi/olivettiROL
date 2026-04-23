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
        self.layout.setContentsMargins(50, 50, 50, 50)
        self.layout.setSpacing(20)
        self.status_container = QWidget()
        self.status_layout = QHBoxLayout(self.status_container)
        self.status_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_dot = QLabel()
        self.status_dot.setFixedSize(12, 12)
        self.status_dot.setStyleSheet("background-color: #95a5a6; border-radius: 6px;")
        self.status_text = SubtitleLabel("CONNESSIONE IN CORSO...")
        self.status_text.setStyleSheet("font-weight: bold; margin-left: 10px;")
        self.status_layout.addWidget(self.status_dot)
        self.status_layout.addWidget(self.status_text)
        self.layout.addWidget(self.status_container)

        # INFORMAZIONI LEZIONE
        self.lesson_info = SubtitleLabel("")
        self.lesson_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lesson_info.setStyleSheet("color: #7f8c8d; font-size: 16px;")
        self.layout.addWidget(self.lesson_info)

        # AREA CAMERA
        self.image_label = SubtitleLabel("Inquadrare il volto")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumHeight(400)
        self.image_label.setStyleSheet("""
            border: 2px solid #e2e8f0; 
            border-radius: 20px; 
            background: #f8fafc;
            color: #94a3b8;
        """)
        self.layout.addWidget(self.image_label)

        # MESSAGGI
        self.msg_box = SubtitleLabel("")
        self.msg_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.msg_box)
        self.btn_container = QHBoxLayout()
        self.btn_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_scan = PrimaryPushButton(FIF.PEOPLE, "Scansione")
        self.btn_scan.setFixedWidth(280)
        self.btn_scan.setFixedHeight(55)
        self.btn_scan.clicked.connect(self.run_detection)
        self.btn_container.addWidget(self.btn_scan)
        self.layout.addLayout(self.btn_container)
        self.addSubInterface(self.central_widget, FIF.HOME, 'Totem')

    # --- FUNZIONI ---
    # --- 1. CHECK CLOUD STATUS: CONTROLLO DELLA SESSIONE ATTIVA E AGGIORNAMENTO INTERFACCIA ---
    def check_cloud_status(self):
        try:
            res = requests.get(self.SESSION_URL, timeout=1.5)
            if res.status_code == 200:
                data = res.json()
                if data.get("active"):
                    self.status_dot.setStyleSheet("background-color: #2ecc71; border-radius: 6px;")
                    self.status_text.setText(f"PRONTO - {data['teacher_display']}")
                    self.lesson_info.setText(f"{data['subject']} ({data['range']})")
                    self.btn_scan.setEnabled(True)
                else:
                    self.status_dot.setStyleSheet("background-color: #e74c3c; border-radius: 6px;")
                    self.status_text.setText("IN ATTESA DI ATTIVAZIONE...")
                    self.lesson_info.setText("Sessione non attiva dalla Dashboard")
                    self.btn_scan.setEnabled(False)
        except:
            self.status_text.setText("⚠️ ERRORE CLOUD")
            self.status_dot.setStyleSheet("background-color: #95a5a6; border-radius: 6px;")

    # --- 2. RUN DETECTION: SIMULAZIONE RILEVAMENTO CON IMMAGINE E GESTIONE RISPOSTA ---
    def run_detection(self):
        path, _ = QFileDialog.getOpenFileName(self, "Simula Camera", "", "Images (*.jpg *.png)")
        if not path: return
        
        pixmap = QPixmap(path)
        self.image_label.setPixmap(pixmap.scaled(self.image_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.image_label.setText("")

        try:
            with open(path, 'rb') as f:
                res = requests.post(self.DETECT_URL, files={'image': f}, timeout=5)
                data = res.json()
                if res.status_code == 200:
                    self.msg_box.setText(f"{data['status']}: {data['student_name']}")
                    InfoBar.success(
                        title="Rilevato",
                        content=data['message'],
                        orient=Qt.Orientation.Horizontal,
                        isClosable=True,
                        duration=3000,
                        position=InfoBarPosition.TOP,
                        parent=self
                    )
                else:
                    self.msg_box.setText("ACCESSO NEGATO")
                    InfoBar.error(
                        title="Errore",
                        content=data['message'],
                        orient=Qt.Orientation.Horizontal,
                        isClosable=True,
                        duration=3000,
                        position=InfoBarPosition.TOP,
                        parent=self
                    )
        except Exception as e:
            InfoBar.warning(
                title="Offline",
                content="Server non raggiungibile",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                duration=3000,
                position=InfoBarPosition.TOP,
                parent=self
            )

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AttendanceTotem()
    window.show()
    sys.exit(app.exec())