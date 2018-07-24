from PyQt5.QtWidgets import QSlider
from PyQt5.QtCore import Qt
from math import log10

# Logarithmic math refresher:
# BOP Base, Outcome Power;
# log(B)(O) = P --> log(2)(64) = 6  ||  log(10)(1000) = 3
#       B^P = O -->        2^6 = 64 ||           10^3 = 1000

class LogarithmicSlider(QSlider):
    def __init__(self, parent):
        super(LogarithmicSlider, self).__init__(parent)

        self.setOrientation(Qt.Horizontal)
        self.analysis_tab = parent

        self.resolution_pow = 5 # Must always be integer higher than 3
        self.slider_resolution = 10**self.resolution_pow

        self.setMinimum(0.001)
        # self.setMaximum(self.slider_resolution)
        self.setMaximum(100)

    def setLogValue(self, value):
        # value = float(value)
        # log_val = log10(value)
        # log_val += (self.resolution_pow - 3)
        # order = self.find_order(log_val)
        # self.setValue(value*(10**order))
        value = float(value)
        log_val = log10(value)
        log_val += 3
        log_val*20
        self.setValue(log_val)

    def logValue(self, value=None):
        if value == None:
            value = self.value()
        value = float(value)
        log_val = log10(value)
        order = self.find_order(log_val)

        logarithmic = value*(10**(order - self.resolution_pow))
        return logarithmic

    def find_order(self, log_val):
        for i in range(self.resolution_pow):
            j = i + 1
            if log_val >= i and log_val < j:
                return float(i)
        return None