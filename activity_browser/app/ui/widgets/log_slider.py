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

        self.setMinimum(1)
        self.setMaximum(100)

    def setLogValue(self, value):
        """ Modify value from 0.001-100 to 1-100 logarithmically and set slider to value. """
        value = int(float(value)*(10**3))
        log_val = round(log10(value), 3)
        set_val = log_val*20
        self.setValue(set_val)

    def logValue(self, value=None):
        """ Read (slider) value and modify it from 1-100 to 0.001-100 logarithmically with relevant rounding. """
        if value == None:
            value = self.value()
        value = float(value)
        log_val = log10(value)
        power = log_val * 2.5 - 3
        ret_val = 10**power

        if log10(ret_val) < -1:
            ret_val = round(ret_val, 3)
        elif log10(ret_val) < -0:
            ret_val = round(ret_val, 2)
        elif log10(ret_val) < 1:
            ret_val = round(ret_val, 1)
        else:
            ret_val = int(round(ret_val, 0))
        return ret_val