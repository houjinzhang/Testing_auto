from PyQt6.QtCore import QObject, pyqtSignal

class Bridge(QObject):
    log_signal = pyqtSignal(str)
    case_count_signal = pyqtSignal(int)
    progress_signal = pyqtSignal(int)

    def __init__(self):
        super().__init__()
