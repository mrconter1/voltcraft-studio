"""Icon factory for Voltcraft Studio"""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import (
    QIcon, QPixmap, QPainter, QColor, QFont, 
    QPen, QPainterPath, QLinearGradient
)
from constants import (
    COLOR_GOLD, COLOR_DARK_GOLD, COLOR_DARKER_GOLD,
    COLOR_BLACK, WINDOW_ICON_SIZE, FOLDER_ICON_SIZE
)


class IconFactory:
    """Factory class for creating application icons"""
    
    @staticmethod
    def create_window_icon() -> QIcon:
        """Create the main window icon - black circle with golden border and lightning bolt"""
        pixmap = QPixmap(WINDOW_ICON_SIZE, WINDOW_ICON_SIZE)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw black circle background
        painter.setBrush(COLOR_BLACK)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(2, 2, 60, 60)
        
        # Draw golden border
        pen = QPen(COLOR_GOLD, 4)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(2, 2, 60, 60)
        
        # Draw lightning bolt emoji in the middle
        font = QFont("Segoe UI Emoji", 36)
        painter.setFont(font)
        painter.setPen(COLOR_GOLD)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "⚡")
        
        painter.end()
        return QIcon(pixmap)
    
    @staticmethod
    def create_folder_icon() -> QIcon:
        """Create a modern folder open icon"""
        pixmap = QPixmap(FOLDER_ICON_SIZE, FOLDER_ICON_SIZE)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw folder body
        folder_path = QPainterPath()
        folder_path.moveTo(12, 24)
        folder_path.lineTo(12, 52)
        folder_path.lineTo(52, 52)
        folder_path.lineTo(52, 24)
        folder_path.lineTo(12, 24)
        
        # Draw folder tab
        tab_path = QPainterPath()
        tab_path.moveTo(12, 24)
        tab_path.lineTo(12, 18)
        tab_path.lineTo(30, 18)
        tab_path.lineTo(32, 24)
        tab_path.lineTo(12, 24)
        
        # Fill folder with gradient
        gradient = QLinearGradient(0, 18, 0, 52)
        gradient.setColorAt(0, COLOR_GOLD)
        gradient.setColorAt(1, COLOR_DARK_GOLD)
        
        painter.setBrush(gradient)
        painter.setPen(QPen(COLOR_DARKER_GOLD, 2))
        painter.drawPath(tab_path)
        painter.drawPath(folder_path)
        
        # Draw document lines inside
        painter.setPen(QPen(QColor(255, 255, 255, 150), 2))
        painter.drawLine(20, 32, 44, 32)
        painter.drawLine(20, 38, 44, 38)
        painter.drawLine(20, 44, 36, 44)
        
        painter.end()
        return QIcon(pixmap)

