import sys
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
import cv2


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.vbox = QVBoxLayout()
        self.feedLabel = QLabel()
        self.vbox.addWidget(self.feedLabel)
        self.cancelBtn = QPushButton("Cancel")
        self.cancelBtn.clicked.connect(self.cancelFeed)
        self.vbox.addWidget(self.cancelBtn)
        self.worker = Worker()
        self.worker.start()
        self.worker.imageUpdate.connect(self.updateFeed)
        self.setLayout(self.vbox)

    def updateFeed(self, image):
        size = self.feedLabel.size()
        width, height = size.width(), size.height()
        image = image.scaled(width, height, Qt.AspectRatioMode.KeepAspectRatio)
        self.feedLabel.setPixmap(QPixmap.fromImage(image))

    def cancelFeed(self):
        self.worker.stop()


class Worker(QThread):

    imageUpdate = pyqtSignal(QImage)

    def run(self):
        self.threadActive = True

        capture = cv2.VideoCapture(0)

        while self.threadActive:
            ret, frame = capture.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = cv2.flip(frame, 1)
                frame = QImage(
                    frame.data,
                    frame.shape[1],
                    frame.shape[0],
                    QImage.Format.Format_RGB888,
                )
                self.imageUpdate.emit(frame)
        
        capture.release()

    def stop(self):
        self.threadActive = False
        self.quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
