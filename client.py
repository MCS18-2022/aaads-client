from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QMainWindow,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QSlider,
    QSizePolicy,
    QFileDialog,
    QStyle,
    QMenu,
    QToolBar,
)
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, QUrl, QObject, pyqtSignal, QThread
import cv2
import os
import sys
from math import log10
from pathlib import Path
import shutil

from annotate import annotated
from img_utils import stream_to_imgs
from db import upload, download_preds


FRAMES_DIR = os.path.join(".", "frames")
FILENAME_PAT = os.path.join(FRAMES_DIR, "frame_{:0{}d}.jpg")


class Worker(QObject):

    framesUploaded = pyqtSignal()
    predsReceived = pyqtSignal()
    vidWriteFinished = pyqtSignal()

    def __init__(self, vid_in_filename, *parents):
        super().__init__(*parents)
        self.vid_in_filename = vid_in_filename

    def run(self):
        vid_in_filename = self.vid_in_filename
        capture = cv2.VideoCapture(vid_in_filename)

        # Retrieve video metadata.
        frame_count = capture.get(cv2.CAP_PROP_FRAME_COUNT)
        id_length = max(int(log10(frame_count)) + 1, 1)
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        dims = (width, height)
        fps = capture.get(cv2.CAP_PROP_FPS)

        # Create a lazy iterator over the images in the input video stream.
        frames = stream_to_imgs(capture)

        # Segment the video into raw frames, and upload them.
        frames_dir = Path(vid_in_filename).stem
        if not os.path.exists(frames_dir):
            os.mkdir(frames_dir)
        for _id, frame in enumerate(frames, start=1):
            frame_out_filename = os.path.join(
                frames_dir, "frame_{:0{}d}.jpg".format(_id, id_length)
            )
            cv2.imwrite(frame_out_filename, frame)
            upload(frame_out_filename)
        
        # Clean up to prevent memory leaks.
        capture.release()
        shutil.rmtree(frames_dir)

        # Push job to server side command queue.
        if not os.path.exists("pending"):
            os.mkdir("pending")
        Path("pending", frames_dir).touch()
        upload(os.path.join("pending", frames_dir))
        shutil.rmtree("pending")

        # Tell the UI thread the frames are uploaded.
        self.framesUploaded.emit()

        # Wait for the model predictions to be available
        # from the server.
        while True:
            preds = download_preds()
            try:
                preds[frames_dir]
                self.predsReceived.emit()
                break
            # If there is no prediction yet, keep waiting.
            except (KeyError, AttributeError, TypeError):
                pass
        
        if not os.path.exists("output"):
            os.mkdir("output")

        # Put the annotations over the video frames, and tie
        # the frames together into a video.
        capture = cv2.VideoCapture(vid_in_filename)
        frames = stream_to_imgs(capture)
        vid_out_filename = os.path.join("output", f"annotated_{frames_dir}.mp4")
        writer = cv2.VideoWriter(
            vid_out_filename, cv2.VideoWriter_fourcc(*"mp4v"), fps, dims
        )
        for frame, pred in zip(frames, preds[frames_dir]):
            frame = annotated(frame, pred)
            writer.write(frame)
        writer.release()

        self.vidWriteFinished.emit()


class MainWindow(QMainWindow):

    TITLE = "Aggressive Action Detector"

    def __init__(self):
        super().__init__()
        self.setWindowTitle(MainWindow.TITLE)
        self.centralWidget = CentralWidget(self)
        self.setCentralWidget(self.centralWidget)
        self._createActions()
        self._createMenuBar()
        self._createToolBar()
        self._createStatusBar()

    def _createMenuBar(self):
        menuBar = self.menuBar()
        fileMenu = QMenu(" &File", self)
        fileMenu.addAction(self.openAction)
        fileMenu.addAction(self.exitAction)
        menuBar.addMenu(fileMenu)

    def _createToolBar(self):
        fileToolBar = QToolBar(" &File", self)
        fileToolBar.addAction(self.openAction)
        fileToolBar.addAction(self.exitAction)
        fileToolBar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, fileToolBar)

    def _createActions(self):
        style = self.style()
        openIcon = style.standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton)
        self.openAction = QAction(openIcon, " &Open...", self)
        self.openAction.triggered.connect(self._process_video)
        exitIcon = style.standardIcon(QStyle.StandardPixmap.SP_BrowserStop)
        self.exitAction = QAction(exitIcon, " &Exit", self)
        self.exitAction.triggered.connect(MainWindow._exit_app)
    
    def _createStatusBar(self):
        self.statusBar = self.statusBar()
        self.statusBar.showMessage("On standby...")

    def _process_video(self):
        # Open a stream for reading the input video.
        vid_in_filename, _ = QFileDialog.getOpenFileName(self, "Select video (.mp4)...")
        if vid_in_filename == "":
            return
        if not vid_in_filename.endswith((".mp4", ".MP4")):
            self.statusBar.showMessage(f"Attempted to process a non-supported file ({Path(vid_in_filename).name})")
            return

        frames_dir = Path(vid_in_filename).stem
        vid_out_filename = os.path.join("output", f"annotated_{frames_dir}.mp4")

        self.thread = QThread()
        self.worker = Worker(vid_in_filename)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.vidWriteFinished.connect(self.thread.quit)
        self.worker.vidWriteFinished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()
        self.statusBar.showMessage("Uploading video frames...")
        self.worker.framesUploaded.connect(lambda: self.statusBar.showMessage("Waiting for model predictions..."))
        self.worker.predsReceived.connect(lambda: self.statusBar.showMessage("Writing video to file..."))
        self.worker.vidWriteFinished.connect(lambda: self.statusBar.showMessage("On standby..."))
        self.thread.finished.connect(
            lambda: self.centralWidget.loadVideo(vid_out_filename)
        )

    @staticmethod
    def _exit_app():
        QApplication.instance().quit()


class CentralWidget(QWidget):
    def __init__(self, *parents):
        super().__init__(*parents)

        # Create video player.
        self.player = VideoPlayer(self)
        videoWidget = QVideoWidget(self)
        self.player.setVideoOutput(videoWidget)

        self.playBtn = PlayBtn(self)
        self.currentTimeDisplay = TimeDisplay()
        self.slider = VideoSlider(self)
        self.totalTimeDisplay = TimeDisplay()

        # Place the widgets in.
        hbox = QHBoxLayout()
        hbox.addWidget(self.playBtn)
        hbox.addWidget(self.currentTimeDisplay)
        hbox.addWidget(self.slider)
        hbox.addWidget(self.totalTimeDisplay)

        vbox = QVBoxLayout()
        vbox.addWidget(videoWidget)
        vbox.addLayout(hbox)

        self.setLayout(vbox)

        # Set event listener.
        self.playBtn.clicked.connect(self.player.updateState)
        self.player.playbackStateChanged.connect(self.onPlaybackStateChanged)
        self.player.durationChanged.connect(self.onPlayerDurationChange)
        self.player.positionChanged.connect(self.onPlayerPositionChange)
        self.slider.sliderMoved.connect(self.onSliderMove)

    def loadVideo(self, filename):
        src = QUrl.fromLocalFile(filename)
        self.player.setSource(src)
        self.player.play()
        self.playBtn.setEnabled(True)

    def onPlaybackStateChanged(self, state):
        self.playBtn.updateState(state)
        if state == VideoPlayer.PlaybackState.StoppedState:
            self.player.play()

    def onPlayerDurationChange(self, duration):
        self.slider.setRangeMax(duration)
        self.totalTimeDisplay.updateTime(duration)

    def onPlayerPositionChange(self, duration):
        self.slider.setValue(duration)
        self.currentTimeDisplay.updateTime(duration)

    def onSliderMove(self, duration):
        self.player.setPosition(duration)
        self.currentTimeDisplay.updateTime(duration)


class VideoPlayer(QMediaPlayer):
    def updateState(self):
        if self.playbackState() == VideoPlayer.PlaybackState.PlayingState:
            self.pause()
        else:
            self.play()


class PlayBtn(QPushButton):

    PLAY = QStyle.StandardPixmap.SP_MediaPlay
    PAUSE = QStyle.StandardPixmap.SP_MediaPause

    def __init__(self, *parents):
        super().__init__(*parents)

        # Store the icons.
        style = self.style()
        self.playIcon = style.standardIcon(PlayBtn.PLAY)
        self.pauseIcon = style.standardIcon(PlayBtn.PAUSE)

        self.setIcon(self.playIcon)
        self.setEnabled(False)

    def updateState(self, state):
        self.setIcon(
            self.pauseIcon
            if state == QMediaPlayer.PlaybackState.PlayingState
            else self.playIcon
        )


class TimeDisplay(QLabel):

    START = 0

    def __init__(self, *parents):
        super().__init__(*parents)
        start_time = TimeDisplay.timestamp_of(TimeDisplay.START)
        self.setText(start_time)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

    def updateTime(self, milliseconds):
        timestamp = TimeDisplay.timestamp_of(milliseconds)
        self.setText(timestamp)

    @staticmethod
    def timestamp_of(milliseconds):
        seconds = milliseconds // 1000
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        timestamp = f"{hours:2}:{minutes:02}:{seconds:02}"
        return timestamp


class VideoSlider(QSlider):

    ORIENTATION = Qt.Orientation.Horizontal
    START = 0

    def __init__(self, *parents):
        super().__init__(VideoSlider.ORIENTATION, *parents)
        self.setRange(VideoSlider.START, VideoSlider.START)

    def setRangeMax(self, range_max):
        self.setRange(VideoSlider.START, range_max)


if __name__ == "__main__":
    # Instantiate the application.
    app = QApplication(sys.argv)

    # Display the GUI.
    main_window = MainWindow()
    main_window.showMaximized()

    # Enter the program main loop.
    sys.exit(app.exec())
