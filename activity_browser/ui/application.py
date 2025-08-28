import sys

from pathlib import Path
from logging import getLogger

from qtpy import QtGui, QtWidgets, QtCore, PYSIDE6
from qtpy.QtCore import Qt
from qtpy.QtGui import QFontDatabase

from activity_browser.static import fonts, icons

log = getLogger(__name__)


class ABApplication(QtWidgets.QApplication):
    _main_window = None
    _controllers = None

    windows = []

    def __init__(self, *args, **kwargs):
        QtCore.QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
        QtCore.QCoreApplication.setAttribute(Qt.AA_UseSoftwareOpenGL)

        super().__init__(*args, **kwargs)
        self.set_icon()  # needs to be called right after super().__init__

        QtGui.QGuiApplication.setAttribute(Qt.AA_DontShowIconsInMenus, True)

        self.add_fonts()

        if PYSIDE6:
            self.pyside6_setup()

    def add_fonts(self):
        QFontDatabase.addApplicationFont(fonts.__path__[0] + "/mono.ttf")
        QFontDatabase.addApplicationFont(fonts.__path__[0] + "/ptsans.ttf")
        QFontDatabase.addApplicationFont(fonts.__path__[0] + "/notosans.ttf")

    def set_icon(self):
        app_icon = QtGui.QIcon(str(Path(icons.__path__[0]).joinpath("main", "ab-small.png")))
        self.setWindowIcon(app_icon)

    def pyside6_setup(self):
        from qtpy.QtWebEngineQuick import QtWebEngineQuick
        QtWebEngineQuick.initialize()

        style = QtWidgets.QStyleFactory().create("fusion")
        self.setStyle(style)

        self.styleHints().colorSchemeChanged.connect(self.check_palette)
        self.check_palette(self.styleHints().colorScheme())

    def check_palette(self, color_scheme):
        import matplotlib.pyplot as plt

        if color_scheme == Qt.ColorScheme.Dark:
            palette = self.style().standardPalette()
            palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(53, 53, 53))

            plt.style.use("dark_background")

            # os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--force-dark-mode"
        else:
            palette = self.style().standardPalette()

            plt.style.use("default")

            # os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = ""
        self.setPalette(palette)

    @property
    def main_window(self) -> QtWidgets.QMainWindow:
        """Returns the main_window widget of the Activity Browser"""
        if self._main_window:
            return self._main_window
        raise Exception(
            "main_window not yet initialized, did you try to access it during startup?"
        )

    @main_window.setter
    def main_window(self, widget: QtWidgets.QMainWindow):
        self._main_window = widget

    def show(self):
        self.main_window.showMaximized()

    def close(self):
        for child in self.children():
            if hasattr(child, "close"):
                child.close()

    def deleteLater(self):
        self.main_window.deleteLater()


application = ABApplication()



#
# if QSysInfo.productType() == "osx":
#     # https://bugreports.qt.io/browse/QTBUG-87014
#     # https://bugreports.qt.io/browse/QTBUG-85546
#     # https://github.com/mapeditor/tiled/issues/2845
#     # https://doc.qt.io/qt-5/qoperatingsystemversion.html#MacOSBigSur-var
#     supported = {"10.10", "10.11", "10.12", "10.13", "10.14", "10.15", "13.6"}
#     if QSysInfo.productVersion() not in supported:
#         os.environ["QT_MAC_WANTS_LAYER"] = "1"
#         os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu"
#         log.info("Info: GPU hardware acceleration disabled")
#
# # on macos buttons silently crashes the renderer without any logs
# # confirmed that buttons works on the latest version of qt using pyside6
# if QSysInfo.productType() in ["arch", "nixos", "osx"]:
#     os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "{} --no-sandbox".format(
#         os.getenv("QTWEBENGINE_CHROMIUM_FLAGS")
#     )
#     log.info("Info: QtWebEngine sandbox disabled")
