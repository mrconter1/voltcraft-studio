import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, 
    QPushButton, QVBoxLayout, QWidget, QFileDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QPen


class TextViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Voltcraft Studio")
        self.setGeometry(100, 100, 800, 600)
        
        # Create and set a cute icon
        self.setWindowIcon(self.create_icon())
        
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
    
    def create_icon(self):
        # Create a black circle with golden border and lightning bolt
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw black circle background
        painter.setBrush(QColor(0, 0, 0))  # Black
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(2, 2, 60, 60)
        
        # Draw golden border
        pen = QPen(QColor(255, 215, 0), 4)  # Gold color, 4px width
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(2, 2, 60, 60)
        
        # Draw lightning bolt emoji in the middle
        font = QFont("Segoe UI Emoji", 36)
        painter.setFont(font)
        painter.setPen(QColor(255, 215, 0))  # Gold color for bolt
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "⚡")
        
        painter.end()
        return QIcon(pixmap)
    
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
                    self.setWindowTitle(f"Voltcraft Studio - {file_path}")
            except Exception as e:
                self.text_edit.setPlainText(f"Error opening file: {str(e)}")


def main():
    app = QApplication(sys.argv)
    viewer = TextViewer()
    viewer.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

