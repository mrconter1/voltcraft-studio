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
    
    @staticmethod
    def create_help_icon() -> QIcon:
        """Create a help/info icon with question mark"""
        pixmap = QPixmap(FOLDER_ICON_SIZE, FOLDER_ICON_SIZE)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw circle background with blue gradient
        gradient = QLinearGradient(0, 0, 0, 64)
        gradient.setColorAt(0, QColor(66, 133, 244))  # Google Blue
        gradient.setColorAt(1, QColor(51, 103, 214))  # Darker blue
        
        painter.setBrush(gradient)
        painter.setPen(QPen(QColor(41, 98, 204), 2))
        painter.drawEllipse(4, 4, 56, 56)
        
        # Draw question mark in white
        font = QFont("Arial", 32, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "?")
        
        painter.end()
        return QIcon(pixmap)
    
    @staticmethod
    def create_move_icon() -> QIcon:
        """Create a move/pan icon (hand cursor)"""
        pixmap = QPixmap(FOLDER_ICON_SIZE, FOLDER_ICON_SIZE)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw hand shape
        hand_path = QPainterPath()
        
        # Palm
        hand_path.moveTo(20, 40)
        hand_path.lineTo(20, 50)
        hand_path.lineTo(35, 50)
        hand_path.lineTo(35, 40)
        
        # Fingers
        # Thumb
        hand_path.moveTo(20, 40)
        hand_path.lineTo(15, 35)
        hand_path.lineTo(15, 25)
        hand_path.lineTo(20, 25)
        hand_path.lineTo(20, 40)
        
        # Index finger
        hand_path.moveTo(22, 40)
        hand_path.lineTo(22, 20)
        hand_path.lineTo(26, 20)
        hand_path.lineTo(26, 40)
        
        # Middle finger
        hand_path.moveTo(28, 40)
        hand_path.lineTo(28, 15)
        hand_path.lineTo(32, 15)
        hand_path.lineTo(32, 40)
        
        # Ring finger
        hand_path.moveTo(34, 40)
        hand_path.lineTo(34, 20)
        hand_path.lineTo(38, 20)
        hand_path.lineTo(38, 40)
        hand_path.lineTo(35, 40)
        
        # Fill hand with gray gradient
        gradient = QLinearGradient(0, 15, 0, 50)
        gradient.setColorAt(0, QColor(230, 230, 230))
        gradient.setColorAt(1, QColor(180, 180, 180))
        
        painter.setBrush(gradient)
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        painter.drawPath(hand_path)
        
        painter.end()
        return QIcon(pixmap)
    
    @staticmethod
    def create_tape_measure_icon() -> QIcon:
        """Create a tape measure icon (ruler with measurement marks)"""
        pixmap = QPixmap(FOLDER_ICON_SIZE, FOLDER_ICON_SIZE)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw ruler body
        gradient = QLinearGradient(0, 20, 0, 44)
        gradient.setColorAt(0, COLOR_GOLD)
        gradient.setColorAt(1, COLOR_DARK_GOLD)
        
        painter.setBrush(gradient)
        painter.setPen(QPen(COLOR_DARKER_GOLD, 2))
        painter.drawRect(12, 20, 40, 24)
        
        # Draw measurement marks
        painter.setPen(QPen(COLOR_BLACK, 1.5))
        for i in range(5):
            x = 16 + i * 8
            # Alternate between long and short marks
            if i % 2 == 0:
                painter.drawLine(x, 22, x, 30)
            else:
                painter.drawLine(x, 22, x, 27)
        
        # Draw numbers
        font = QFont("Arial", 8, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(COLOR_BLACK)
        painter.drawText(16, 40, "0")
        painter.drawText(38, 40, "Δt")
        
        painter.end()
        return QIcon(pixmap)

