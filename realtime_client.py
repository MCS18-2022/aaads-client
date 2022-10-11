from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from db import *
import cv2
from pathlib import Path
import sys
from annotate import annotated


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.vbox = QVBoxLayout()
        self.feed = QLabel()
        self.vbox.addWidget(self.feed)
        self.cancelBtn = QPushButton("Cancel")
        self.cancelBtn.clicked.connect(self.cancelFeed)
        self.vbox.addWidget(self.cancelBtn)
        self.worker = Worker()
        self.worker.start()
        self.worker.feedUpdated.connect(self.updateFeed)
        self.setLayout(self.vbox)

    def updateFeed(self, frame):
        size = self.feed.size()
        width, height = size.width(), size.height()
        frame = frame.scaled(width, height, Qt.AspectRatioMode.KeepAspectRatio)
        self.feed.setPixmap(QPixmap.fromImage(frame))

    def cancelFeed(self):
        self.worker.stop()


class Worker(QThread):

    feedUpdated = pyqtSignal(QImage)

    def run(self):
        self.threadActive = True

        capture = cv2.VideoCapture(0)
        _id = 1

        while self.threadActive:
            ret, frame = capture.read()
            if ret:

                frame = cv2.flip(frame, 1)

                path = Path("webcam_up", f"frame_{_id:05}.png")
                cv2.imwrite(str(path), frame)
                upload(str(path))
                realtime_db_ref.child("pending").set({"id": path.stem})
                while True:
                    model_predictions = realtime_db_ref.child(path.stem).get()
                    if model_predictions is not None:
                        break
                if "predictions" in model_predictions:
                    frame = annotated(frame, model_predictions["predictions"])
                print("Time taken:", model_predictions["inference_time"])
                _id += 1

                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = QImage(
                    frame.data,
                    frame.shape[1],
                    frame.shape[0],
                    QImage.Format.Format_RGB888,
                )

                self.feedUpdated.emit(frame)

        capture.release()

    def stop(self):
        self.threadActive = False
        self.quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec())
