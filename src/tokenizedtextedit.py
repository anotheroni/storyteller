from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QTextEdit
from PyQt5.QtCore import QObject, QThread, pyqtSlot
from PyQt5.QtGui import QFocusEvent

from src.llm import CountTask

class CustomTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super(CustomTextEdit, self).__init__(parent)
        self.parent = parent
    def focusOutEvent(self, event: QFocusEvent) -> None:
        if self.CustomTextEdit_oldText != self.toPlainText():
            self.CustomTextEdit_oldText = self.toPlainText()
            self.parent.updateTokens()
        super().focusOutEvent(event)
    def focusInEvent(self, event: QFocusEvent) -> None:
        self.CustomTextEdit_oldText = self.toPlainText()
        super().focusInEvent(event)

class TokenizedTextEdit(QWidget):
    def __init__(self, worker):
        super().__init__()
        self.worker = worker
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.tokenCountLabel = QLabel()
        self.tokenCount = 0
        self.textEdit = CustomTextEdit(self)
        self.layout.addWidget(self.textEdit)
        self.layout.addWidget(self.tokenCountLabel)

    def setText(self, text):
        if self.textEdit.toPlainText() != text:
            self.textEdit.setText(text)
            self.updateTokens()
    def setPlainText(self, text):
        if self.textEdit.toPlainText() != text:
            self.textEdit.setPlainText(text)
            self.updateTokens()
    def setPlaceholderText(self, text):
        return self.textEdit.setPlaceholderText(text)
    def getText(self):
        return self.textEdit.toPlainText()
    def toPlainText(self):
        return self.textEdit.toPlainText()

    #Bypass token counting when we already know it or it's not relevant
    #a negative token count triggers an update anyway
    def setPlainTextAndTokens(self, text, tokens):
        self.textEdit.setPlainText(text)
        if tokens < 0:
            self.updateTokens()
        else:
            self.onTokensCounted(tokens)

    def onTokensCounted(self, count):
        self.tokenCount = count
        self.tokenCountLabel.setText("Tokens: " + str(self.tokenCount))

    @pyqtSlot()
    def updateTokens(self):
        self.tokenCountLabel.setText("Counting tokens...")
        task = CountTask(self.textEdit.toPlainText(), self)
        self.worker.addTask(task)

