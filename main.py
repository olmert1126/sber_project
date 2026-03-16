import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QDialog
from PyQt6 import uic

class MyWidget(QDialog):
    def __init__(self):
        super().__init__()
        uic.loadUi('base.ui', self)



if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyWidget()
    ex.show()
    sys.exit(app.exec())