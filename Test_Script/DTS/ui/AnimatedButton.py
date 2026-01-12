from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import QPropertyAnimation, QSize, QEasingCurve

class AnimatedButton(QPushButton):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)

        self.hover_anim = QPropertyAnimation(self, b"maximumWidth")
        self.hover_anim.setDuration(180)
        self.hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.base_width = None

    def enterEvent(self, event):
        if self.base_width is None:
            self.base_width = self.width()

        self.hover_anim.stop()
        self.hover_anim.setStartValue(self.width())
        self.hover_anim.setEndValue(self.base_width + 8)
        self.hover_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hover_anim.stop()
        self.hover_anim.setStartValue(self.width())
        self.hover_anim.setEndValue(self.base_width)
        self.hover_anim.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self.setStyleSheet("transform: scale(0.95);")
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.setStyleSheet("transform: scale(1);")
        super().mouseReleaseEvent(event)

