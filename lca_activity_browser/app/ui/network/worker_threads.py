import brightway2 as bw
from PyQt5 import QtCore
from .signals import sankeysignals


class GraphTraversalThread(QtCore.QThread):
    def update_params(self, demand, method, cutoff, max_calc):
        self.demand = demand
        self.method = method
        self.cutoff = cutoff
        self.max_calc = max_calc
        
    def run(self):
        res = bw.GraphTraversal().calculate(self.demand, self.method, self.cutoff, self.max_calc)
        sankeysignals.gt_ready.emit(res)


gt_worker_thread = GraphTraversalThread()

