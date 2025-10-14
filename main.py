import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, 
    QPushButton, QVBoxLayout, QWidget, QFileDialog
)
from PyQt6.QtCore import Qt


class TextViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple Text Viewer")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create Open button
        self.open_button = QPushButton("Open File")
        self.open_button.clicked.connect(self.open_file)
        layout.addWidget(self.open_button)
        
        # Create text display area
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        layout.addWidget(self.text_edit)
    
    def open_file(self):
        # Open file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Text File",
            "",
            "Text Files (*.txt);;All Files (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    self.text_edit.setPlainText(content)
                    self.setWindowTitle(f"Simple Text Viewer - {file_path}")
            except Exception as e:
                self.text_edit.setPlainText(f"Error opening file: {str(e)}")


def main():
    app = QApplication(sys.argv)
    viewer = TextViewer()
    viewer.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

