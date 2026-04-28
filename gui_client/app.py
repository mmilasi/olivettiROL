import sys
import os
import requests
from PyQt6.QtWidgets import QApplication, QFileDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QGraphicsOpacityEffect
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath, QBrush, QColor
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve

from qfluentwidgets import (FluentWindow, SubtitleLabel, PrimaryPushButton, 
                            InfoBar, InfoBarPosition, Theme, setTheme)
from qfluentwidgets import FluentIcon as FIF

class AttendanceTotem(FluentWindow):
    def __init__(self) -> None:
        super().__init__()
        self.SESSION_URL = "http://127.0.0.1:5001/api/active_session"
        self.DETECT_URL = "http://127.0.0.1:5002/detect"
        
        self.setWindowTitle("ROL Totem - Terminale Presenze")
        self.resize(500, 700) 
        self.navigationInterface.hide() 
        self.hBoxLayout.setContentsMargins(0, 0, 0, 0)
        self._setup_ui()
        setTheme(Theme.LIGHT)
        self.set_camera_placeholder()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_cloud_status)
        self.timer.start(3000)

    def _setup_ui(self):
        self.central_widget = QWidget()
        self.central_widget.setObjectName("totemInterface") 
        
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(50, 40, 50, 40)
        self.layout.setSpacing(10)

        # --- 1. RIGA STATO ---
        self.status_container = QWidget()
        self.status_layout = QHBoxLayout(self.status_container)
        self.status_dot = QLabel()
        self.status_dot.setFixedSize(12, 12)
        self.status_dot.setStyleSheet("background-color: #95a5a6; border-radius: 6px;")
        self.status_text = SubtitleLabel("CONNESSIONE...")
        self.status_text.setStyleSheet("font-weight: 800; font-size: 20px; margin-left: 10px;")
        self.status_layout.addWidget(self.status_dot)
        self.status_layout.addWidget(self.status_text)
        self.layout.addWidget(self.status_container, 0, Qt.AlignmentFlag.AlignCenter)

        # --- 2. INFO LEZIONE ---
        self.combined_info = SubtitleLabel("")
        self.combined_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.combined_info.setStyleSheet("color: #475569; font-weight: 500; font-size: 15px;")
        self.layout.addWidget(self.combined_info)
        self.layout.addSpacing(10)

        # --- 3. AREA CAMERA ---
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumHeight(400)
        self.layout.addWidget(self.image_label)

        # --- 4. FEEDBACK SOTTO LA FOTO ---
        self.msg_box = SubtitleLabel("")
        self.msg_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.msg_box)

        # --- 5. PULSANTE ---
        self.btn_scan = PrimaryPushButton(FIF.PEOPLE, "Scansione Facciale")
        self.btn_scan.setFixedWidth(300)
        self.btn_scan.setFixedHeight(60)
        self.btn_scan.clicked.connect(self.run_detection)
        self.layout.addWidget(self.btn_scan, 0, Qt.AlignmentFlag.AlignCenter)

        self.addSubInterface(self.central_widget, FIF.HOME, 'Totem')

    def get_rounded_pixmap(self, pixmap, radius):
        target = QPixmap(pixmap.size())
        target.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(target)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        path = QPainterPath()
        path.addRoundedRect(0, 0, pixmap.width(), pixmap.height(), radius, radius)
        
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()
        return target

    def set_camera_placeholder(self):
        self.image_label.setPixmap(QPixmap())
        placeholder_html = """
            <div style='text-align: center;'>
                <p style='font-size: 60px; margin-bottom: 20px;'>📷</p>
                <p style='font-size: 18px; font-weight: 800; color: #1e293b; margin-bottom: 5px;'>INQUADRARE IL VOLTO</p>
                <p style='font-size: 13px; color: #64748b;'>pronto per la scansione</p>
            </div>
        """
        self.image_label.setText(placeholder_html)
        self.image_label.setStyleSheet("border: 2px dashed #cbd5e1; border-radius: 28px; background: #f8fafc;")
        self.msg_box.setText("")
        self.msg_box.setStyleSheet("font-weight: 600; color: #1e293b; font-size: 16px;")

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
                    self.status_text.setText("NON ATTIVO")
                    self.combined_info.setText("Sessione non attiva")
                    self.btn_scan.setEnabled(False)
        except:
            self.status_text.setText("⚠️ OFFLINE")

    def show_animated_info(self, is_success, message):
        if is_success:
            info = InfoBar.success(
                title="Rilevato",
                content=message,
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.NONE,
                duration=-1,
                parent=self
            )
        else:
            info = InfoBar.error(
                title="Errore",
                content=message,
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.NONE,
                duration=-1,
                parent=self
            )

        info.show()
        x = (self.width() - info.width()) // 2
        y = (self.height() - info.height()) // 2
        info.move(x, y)

        opacity_effect = QGraphicsOpacityEffect(info)
        info.setGraphicsEffect(opacity_effect)

        self.fade_in = QPropertyAnimation(opacity_effect, b"opacity")
        self.fade_in.setDuration(800)
        self.fade_in.setStartValue(0)
        self.fade_in.setEndValue(1)
        self.fade_in.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.fade_in.start()

        def start_fade_out():
            self.fade_out = QPropertyAnimation(opacity_effect, b"opacity")
            self.fade_out.setDuration(800)
            self.fade_out.setStartValue(1)
            self.fade_out.setEndValue(0)
            self.fade_out.setEasingCurve(QEasingCurve.Type.InOutQuad)
            self.fade_out.finished.connect(info.deleteLater)
            self.fade_out.finished.connect(self.set_camera_placeholder)
            self.fade_out.start()

        QTimer.singleShot(3800, start_fade_out)

    def run_detection(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        students_dir = os.path.join(project_root, "img_students")

        path, _ = QFileDialog.getOpenFileName(self, "Camera", students_dir, "Images (*.jpg *.png)")
        if not path: return
        raw_pixmap = QPixmap(path).scaled(self.image_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        rounded_pixmap = self.get_rounded_pixmap(raw_pixmap, 28)        
        self.image_label.setPixmap(rounded_pixmap)
        self.image_label.setText("")
        self.image_label.setStyleSheet("border: 2px dashed #cbd5e1; border-radius: 28px; background: #000;")
        self.msg_box.setText("")

        try:
            with open(path, 'rb') as f:
                res = requests.post(self.DETECT_URL, files={'image': f}, timeout=5)
                data = res.json()
                is_success = (res.status_code == 200)
                duration = 5000 
                QTimer.singleShot(1500, lambda: self.show_animated_info(is_success, data['message']))

        except Exception as e:
            w = InfoBar.warning(title="Offline", content="Server non raggiungibile", position=InfoBarPosition.NONE, parent=self)
            w.show()
            w.move((self.width() - w.width()) // 2, (self.height() - w.height()) // 2)
            QTimer.singleShot(2000, self.set_camera_placeholder)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AttendanceTotem()
    window.show()
    sys.exit(app.exec())