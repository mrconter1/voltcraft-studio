"""Icon factory for Voltcraft Studio"""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import (
    QIcon, QPixmap, QPainter, QColor, QFont, 
    QPen, QPainterPath, QLinearGradient
)
import qtawesome as qta
from .constants import (
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
        """Create a folder open icon using Font Awesome"""
        return qta.icon('fa6s.folder-open', color=COLOR_GOLD)
    
    @staticmethod
    def create_help_icon() -> QIcon:
        """Create a help/info icon using Font Awesome"""
        return qta.icon('fa6s.circle-question', color=COLOR_GOLD)
    
    @staticmethod
    def create_move_icon() -> QIcon:
        """Create a move/pan icon using Font Awesome"""
        return qta.icon('fa6s.arrows-up-down-left-right', color=COLOR_GOLD)
    
    @staticmethod
    def create_tape_measure_icon() -> QIcon:
        """Create a tape measure icon using Font Awesome"""
        return qta.icon('fa6s.ruler-vertical', color=COLOR_GOLD)
    
    @staticmethod
    def create_binarize_icon() -> QIcon:
        """Create a binarize icon using Font Awesome"""
        return qta.icon('fa6s.spray-can-sparkles', color=COLOR_GOLD)
    
    @staticmethod
    def create_decode_icon() -> QIcon:
        """Create a decode/mapping icon using Font Awesome"""
        return qta.icon('fa6s.square-binary', color=COLOR_GOLD)
    
    @staticmethod
    def create_relative_y_axis_icon() -> QIcon:
        """Create an up-down arrows icon for relative Y-axis adjustment"""
        return qta.icon('fa6s.arrows-up-down', color=COLOR_GOLD)

