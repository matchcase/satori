import sys
import re
from PySide6.QtGui import QTextCursor, QTextCharFormat, QColor, QFont
from PySide6.QtWidgets import QApplication, QMainWindow, QTextEdit
from PySide6.QtCore import Qt

class TextEditor(QTextEdit):
    def __init__(self):
        super().__init__()
        self.tilde_mode = False
        self.first_move = False

    def keyPressEvent(self, event):
        cursor = self.textCursor()

        if event.key() == Qt.Key_AsciiTilde:
            if self.tilde_mode and self.first_move:
                self.tilde_mode = False
                cursor.deletePreviousChar()
                cursor.insertText("~")
                return
            else:
                self.tilde_mode = True
                self.first_move = True
                format = QTextCharFormat()
                format.setBackground(QColor("lightblue"))
                cursor.insertText("~", format)
                return

        if self.tilde_mode:
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                self.tilde_mode = False
                self.first_move = False
                process_ai(self.toPlainText())
                self.deleteLightBlueText()
                format = QTextCharFormat()
                format.setBackground(QColor("white"))
                cursor.insertText("\n", format)
                return
            elif event.key() == Qt.Key_Backspace:
                if self.first_move:
                    self.tilde_mode = False
                    self.first_move = False
                cursor.deletePreviousChar()
                return
            elif event.text():
                self.first_move = False
                format = QTextCharFormat()
                format.setBackground(QColor("lightblue"))
                cursor.insertText(event.text(), format)
                return

        self.first_move = False
        super().keyPressEvent(event)

    def deleteLightBlueText(self):
        """Delete all light-blue-colored text from the editor."""
        cursor = self.textCursor()
        cursor.beginEditBlock()
    
        cursor.movePosition(QTextCursor.Start)
        while not cursor.atEnd():
            cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor)
            char_format = cursor.charFormat()
            if char_format.background().color() == QColor("lightblue"):
                cursor.removeSelectedText()
            else:
                cursor.clearSelection()
    
        cursor.endEditBlock()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tilde Text Editor")
        self.setGeometry(100, 100, 800, 600)

        self.text_edit = TextEditor()
        self.setCentralWidget(self.text_edit)

    def increaseFontSize(self, size=None):
        font = self.text_edit.font()
        if size is None:
            font.setPointSize(font.pointSize() + 5)
        elif size > 0:
            font.setPointSize(size)
            self.text_edit.setFont(font)

    def decreaseFontSize(self, size=None):
        font = self.text_edit.font()
        if size is None:
            font.setPointSize(font.pointSize() + 5)
        elif size > 0:
            font.setPointSize(size)
            self.text_edit.setFont(font)

def process_ai(text):
    print("Text passed to process_ai():")
    print(text)

    increase_match = re.search(r".*~increase size(?: to (\d+))?", text, re.MULTILINE)
    decrease_match = re.search(r".*~decrease size(?: to (\d+))?", text, re.MULTILINE)

    editor = QApplication.instance().activeWindow()

    if increase_match:
        size = int(increase_match.group(1)) if increase_match.group(1) else None
        editor.increaseFontSize(size)

    elif decrease_match:
        size = int(decrease_match.group(1)) if decrease_match.group(1) else None
        editor.decreaseFontSize(size)

def main():
    app = QApplication(sys.argv)
    editor = MainWindow()
    editor.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
