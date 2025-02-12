import sys
import re
from PySide6.QtGui import QTextCursor, QTextCharFormat, QColor, QFont
from PySide6.QtWidgets import QApplication, QTextEdit
from PySide6.QtCore import Qt
from pygments import highlight
from pygments.lexers import guess_lexer, get_lexer_by_name
from pygments.formatters.html import HtmlFormatter
from bs4 import BeautifulSoup

from langchain_ollama.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import ConfigurableField
from langchain_core.tools import tool
from langchain.agents import create_tool_calling_agent, AgentExecutor

class Editor(QTextEdit):
    def __init__(self):
        super().__init__()
        self.tilde_mode = False
        self.first_move = False
        self.syntax_highlighting_enabled = False
        self.current_language = None

    def keyPressEvent(self, event):
        cursor = self.textCursor()

        # Handle tilde key to enter "tilde mode"
        if event.key() == Qt.Key_AsciiTilde:
            if self.tilde_mode and self.first_move:
                self.tilde_mode = False
                cursor.deletePreviousChar()
                cursor.insertText("~")
                return
            else:
                self.tilde_mode = True
                self.first_move = True
                fmt = QTextCharFormat()
                fmt.setBackground(QColor("lightblue"))
                cursor.insertText("~", fmt)
                return

        # In tilde mode, color subsequent text light blue
        if self.tilde_mode:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                self.tilde_mode = False
                self.first_move = False
                process_ai(self.toPlainText())
                self.deleteLightBlueText()
                fmt = QTextCharFormat()
                fmt.setBackground(QColor("white"))
                cursor.insertText("\n", fmt)
                return
            elif event.key() == Qt.Key_Backspace:
                if self.first_move:
                    self.tilde_mode = False
                    self.first_move = False
                cursor.deletePreviousChar()
                return
            elif event.text():
                self.first_move = False
                fmt = QTextCharFormat()
                fmt.setBackground(QColor("lightblue"))
                cursor.insertText(event.text(), fmt)
                return

        self.first_move = False
        super().keyPressEvent(event)

        if self.syntax_highlighting_enabled:
            self.applySyntaxHighlighting()

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

    def setSyntaxHighlighting(self, language=None):
        """Set the syntax highlighting to a specific language or let Pygments guess."""
        self.current_language = language
        self.applySyntaxHighlighting()

    def toggleSyntaxHighlighting(self, enable=None):
        """
        Toggle syntax highlighting on or off.
        :param enable: Optional argument to explicitly enable or disable.
        """
        if enable is not None:
            self.syntax_highlighting_enabled = enable
        else:
            self.syntax_highlighting_enabled = not self.syntax_highlighting_enabled

        if self.syntax_highlighting_enabled:
            self.applySyntaxHighlighting()
        else:
            self.clearFormatting()

    def applySyntaxHighlighting(self):
        """Apply syntax highlighting to the entire text."""
        text = self.toPlainText()

        # Save the current cursor position
        current_cursor_position = self.textCursor().position()

        # Choose a lexer: either the one set by language or let Pygments guess.
        lexer = get_lexer_by_name(self.current_language) if self.current_language else guess_lexer(text)

        formatter = HtmlFormatter(style="colorful", noclasses=True)
        highlighted_text = highlight(text, lexer, formatter)

        # Extract formatting from the HTML using BeautifulSoup
        soup = BeautifulSoup(highlighted_text, "html.parser")
        plain_text = soup.get_text()

        # Only continue if the plain text matches exactly
        if plain_text != text:
            return

        cursor = self.textCursor()
        cursor.beginEditBlock()

        # Loop through each styled span tag and apply formatting.
        for tag in soup.find_all("span"):
            if tag.string:
                # Find the first occurrence of the tag's text in the plain text.
                start = plain_text.find(tag.string)
                if start != -1:
                    cursor.setPosition(start)
                    cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor, len(tag.string))

                    fmt = QTextCharFormat()
                    style = tag.attrs.get("style", "")
                    if "color" in style:
                        try:
                            color = style.split("color:")[1].split(";")[0].strip()
                            fmt.setForeground(QColor(color))
                        except Exception:
                            pass
                    if "bold" in style:
                        fmt.setFontWeight(QFont.Bold)
                    if "italic" in style:
                        fmt.setFontItalic(True)

                    cursor.setCharFormat(fmt)

        cursor.endEditBlock()

        # Restore the original cursor position.
        cursor.setPosition(current_cursor_position)
        self.setTextCursor(cursor)

    def clearFormatting(self):
        """Clear all formatting from the text."""
        cursor = self.textCursor()
        cursor.select(QTextCursor.Document)
        cursor.setCharFormat(QTextCharFormat())
        cursor.clearSelection()

    def increaseFontSize(self, size=None):
        """Increase the font size."""
        font = self.font()
        size = size or font.pointSize() + 5
        if size > 0:
            font.setPointSize(size)
            self.setFont(font)

    def decreaseFontSize(self, size=None):
        """Decrease the font size."""
        font = self.font()
        size = size or font.pointSize() - 5
        if size > 0:
            font.setPointSize(size)
            self.setFont(font)

def process_ai(text):
    print("Text passed to process_ai():")
    print(text)

    cmd = re.match(r".*~(.*)", text)

    # Get the active window, which is now our Editor widget.
    editor = QApplication.instance().activeWindow()

    @tool
    def tool_increaseFontSize(size=None):
        "Increases font size by (size) points. If no argument is provided, increases by 5 points."
        editor.increaseFontSize(size)

    @tool
    def tool_decreaseFontSize(size=None):
        "Decreases font size by (size) points. If no argument is provided, decreases by 5 points."
        editor.decreaseFontSize(size)

    @tool
    def tool_toggleSyntaxHighlighting():
        "Toggles syntax highlighting for programming languages."
        editor.toggleSyntaxHighlighting()

    tools = [tool_increaseFontSize, tool_decreaseFontSize, tool_toggleSyntaxHighlighting]
    
    llm = ChatOllama(model="mistral-nemo", temperature=0)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an LLM agent that runs commands to manage a text editor. Respond only with tool calls. Use the best tool for satisfying the user's needs. Do not talk to the user."), 
        ("human", "{input}"), 
        ("placeholder", "{agent_scratchpad}"),
       ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    #     size = int(decrease_match.group(1)) if decrease_match.group(1) else None
    #     editor.decreaseFontSize(size)
    # elif syntax_match:
    #     editor.toggleSyntaxHighlighting()


def main():
    app = QApplication(sys.argv)
    editor = Editor()
    editor.setWindowTitle("Satori")
    editor.setGeometry(0, 0, 800, 600)
    editor.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
