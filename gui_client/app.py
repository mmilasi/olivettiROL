import sys
import os
import requests
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout,
    QWidget, QFileDialog, QTextEdit, QCheckBox, QHBoxLayout,
    QStatusBar, QMessageBox, QScrollArea, QLineEdit
)
from PyQt6.QtGui import QAction, QPixmap, QIcon, QTransform
from PyQt6.QtCore import Qt

class AttendanceClient(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        # docker mapping of microservices endpoints
        self.AUTH_URL = "http://localhost:5001/login"
        self.DETECT_URL = "http://localhost:5002/detect"
        
        self.setWindowTitle("ITS Attendance System - Terminale Totem")
        self.setGeometry(100, 100, 500, 800)

        self._init_state()
        self._setup_ui()
        self.set_light_theme()

    def _init_state(self) -> None:
        """Inizializza lo stato dell'applicazione"""
        self.current_image_path = None
        self.auth_token = None
        self.is_logged_in = False
        self.current_theme = "light"

    def _setup_ui(self) -> None:
        """Costruisce l'interfaccia focalizzata sul business case"""
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.root_layout = QVBoxLayout(self.central_widget)

        menubar = self.menuBar()
        if menubar is not None:
            session_menu = menubar.addMenu("Sessione")
            if session_menu is not None:
                login_act = session_menu.addAction("Login Docente (JWT)")
                if login_act is not None:
                    login_act.triggered.connect(self.handle_login)

            view_menu = menubar.addMenu("Aspetto")
            if view_menu is not None:
                light_act = view_menu.addAction("Tema Chiaro")
                if light_act is not None:
                    light_act.triggered.connect(self.set_light_theme)
                
                dark_act = view_menu.addAction("Tema Scuro")
                if dark_act is not None:
                    dark_act.triggered.connect(self.set_dark_theme)
        
        # display (camera feed simulation)
        self.image_label = QLabel("Sistema in attesa.\nEffettuare il Login per attivare il sensore.")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("border: 2px dashed #AAA; border-radius: 10px; background: #EEE; color: #555;")
        self.image_label.setMinimumHeight(400)
        self.root_layout.addWidget(self.image_label)

        # recognition info display box
        self.result_box = QTextEdit()
        self.result_box.setReadOnly(True)
        self.result_box.setPlaceholderText("Risultati del riconoscimento AI...")
        self.result_box.setFixedHeight(120)
        self.root_layout.addWidget(self.result_box)

        # control buttons
        ctrl_layout = QHBoxLayout()
        self.btn_load = QPushButton("Carica/Cattura Foto")
        self.btn_load.setFixedHeight(50)
        self.btn_load.clicked.connect(self.load_image)
        
        self.btn_scan = QPushButton("RILEVA PRESENZA")
        self.btn_scan.setFixedHeight(50)
        self.btn_scan.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.btn_scan.clicked.connect(self.run_detection)
        
        ctrl_layout.addWidget(self.btn_load)
        ctrl_layout.addWidget(self.btn_scan)
        self.root_layout.addLayout(ctrl_layout)

        # report options checkbox
        self.check_report = QCheckBox("Registra automaticamente nel Database Presenze")
        self.check_report.setChecked(True)
        self.root_layout.addWidget(self.check_report)

        # status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    # --- microservices ---

    def handle_login(self):
        """Autenticazione JWT con input dinamico"""
        from PyQt6.QtWidgets import QInputDialog
        
        username, ok1 = QInputDialog.getText(self, 'Login', 'Username:')
        if not ok1 or not username: return

        password, ok2 = QInputDialog.getText(self, 'Login', 'Password:', QLineEdit.EchoMode.Password)
        if not ok2 or not password: return
        
        try:
            credentials = {"username": username, "password": password}
            response = requests.post(self.AUTH_URL, json=credentials)
            
            if response.status_code == 200:
                self.auth_token = response.json().get('token')
                self.is_logged_in = True
                self.status_bar.showMessage(f"Sessione attiva: {username}")
                self.image_label.setText("Sensore Attivo. Caricare foto studente.")
                QMessageBox.information(self, "Login", "Autenticazione riuscita!")
            else:
                QMessageBox.warning(self, "Errore", "Credenziali non valide.")
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Connessione fallita: {e}")

    def run_detection(self):
        """Invia l'immagine al microservizio di rilevamento"""
        if not self.is_logged_in:
            QMessageBox.warning(self, "Accesso Negato", "Login richiesto.")
            return
        
        if not self.current_image_path:
            QMessageBox.warning(self, "Errore", "Caricare una foto prima.")
            return

        self.status_bar.showMessage("Analisi in corso...")
        
        try:
            with open(self.current_image_path, 'rb') as img_file:
                files = {'image': img_file}
                headers = {'Authorization': f'Bearer {self.auth_token}'}
                
                response = requests.post(self.DETECT_URL, files=files, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    res_text = f"STUDENTE: {data.get('student_name')}\n"
                    res_text += f"MATCH: {data.get('confidence')}%\n"
                    res_text += f"ORARIO: {data.get('timestamp')}"
                    self.result_box.setPlainText(res_text)
                    self.status_bar.showMessage("Presenza registrata.")
                else:
                    self.result_box.setPlainText("Errore rilevamento o sessione scaduta.")
        except Exception as e:
            QMessageBox.critical(self, "Errore AI", str(e))

    def load_image(self):
        file, _ = QFileDialog.getOpenFileName(self, "Apri Foto", "", "Images (*.jpg *.png)")
        if file:
            self.current_image_path = file
            pixmap = QPixmap(file)
            scaled = pixmap.scaled(self.image_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.image_label.setPixmap(scaled)
            self.status_bar.showMessage(f"Caricato: {os.path.basename(file)}")

    def set_light_theme(self):
        self.setStyleSheet("QMainWindow { background-color: #F5F5F5; }")
    
    def set_dark_theme(self):
        self.setStyleSheet("QMainWindow { background-color: #2D2D2D; color: white; }")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AttendanceClient()
    window.show()
    sys.exit(app.exec())