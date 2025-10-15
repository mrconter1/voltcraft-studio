"""Icon factory for Voltcraft Studio"""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import (
    QIcon, QPixmap, QPainter, QColor, QFont, 
    QPen, QPainterPath, QLinearGradient
)
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
        """Create a move/pan icon (four-directional arrows)"""
        pixmap = QPixmap(FOLDER_ICON_SIZE, FOLDER_ICON_SIZE)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Center point of the icon
        center_x = FOLDER_ICON_SIZE // 2  # 32
        center_y = FOLDER_ICON_SIZE // 2  # 32
        
        # Arrow parameters
        arrow_length = 18  # Length from center to arrow tip
        arrow_head_size = 7  # Size of arrowhead
        line_width = 3
        
        # Draw circle in center
        painter.setBrush(QColor(200, 200, 200))
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        painter.drawEllipse(center_x - 4, center_y - 4, 8, 8)
        
        # Draw four arrows
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(200, 200, 200))
        
        # Up arrow
        up_arrow = QPainterPath()
        up_arrow.moveTo(center_x, center_y - arrow_length)  # Tip
        up_arrow.lineTo(center_x - arrow_head_size, center_y - arrow_length + arrow_head_size)
        up_arrow.lineTo(center_x - line_width//2, center_y - arrow_length + arrow_head_size)
        up_arrow.lineTo(center_x - line_width//2, center_y - 6)
        up_arrow.lineTo(center_x + line_width//2, center_y - 6)
        up_arrow.lineTo(center_x + line_width//2, center_y - arrow_length + arrow_head_size)
        up_arrow.lineTo(center_x + arrow_head_size, center_y - arrow_length + arrow_head_size)
        up_arrow.closeSubpath()
        painter.drawPath(up_arrow)
        
        # Down arrow
        down_arrow = QPainterPath()
        down_arrow.moveTo(center_x, center_y + arrow_length)  # Tip
        down_arrow.lineTo(center_x - arrow_head_size, center_y + arrow_length - arrow_head_size)
        down_arrow.lineTo(center_x - line_width//2, center_y + arrow_length - arrow_head_size)
        down_arrow.lineTo(center_x - line_width//2, center_y + 6)
        down_arrow.lineTo(center_x + line_width//2, center_y + 6)
        down_arrow.lineTo(center_x + line_width//2, center_y + arrow_length - arrow_head_size)
        down_arrow.lineTo(center_x + arrow_head_size, center_y + arrow_length - arrow_head_size)
        down_arrow.closeSubpath()
        painter.drawPath(down_arrow)
        
        # Left arrow
        left_arrow = QPainterPath()
        left_arrow.moveTo(center_x - arrow_length, center_y)  # Tip
        left_arrow.lineTo(center_x - arrow_length + arrow_head_size, center_y - arrow_head_size)
        left_arrow.lineTo(center_x - arrow_length + arrow_head_size, center_y - line_width//2)
        left_arrow.lineTo(center_x - 6, center_y - line_width//2)
        left_arrow.lineTo(center_x - 6, center_y + line_width//2)
        left_arrow.lineTo(center_x - arrow_length + arrow_head_size, center_y + line_width//2)
        left_arrow.lineTo(center_x - arrow_length + arrow_head_size, center_y + arrow_head_size)
        left_arrow.closeSubpath()
        painter.drawPath(left_arrow)
        
        # Right arrow
        right_arrow = QPainterPath()
        right_arrow.moveTo(center_x + arrow_length, center_y)  # Tip
        right_arrow.lineTo(center_x + arrow_length - arrow_head_size, center_y - arrow_head_size)
        right_arrow.lineTo(center_x + arrow_length - arrow_head_size, center_y - line_width//2)
        right_arrow.lineTo(center_x + 6, center_y - line_width//2)
        right_arrow.lineTo(center_x + 6, center_y + line_width//2)
        right_arrow.lineTo(center_x + arrow_length - arrow_head_size, center_y + line_width//2)
        right_arrow.lineTo(center_x + arrow_length - arrow_head_size, center_y + arrow_head_size)
        right_arrow.closeSubpath()
        painter.drawPath(right_arrow)
        
        # Add dark outline to all arrows
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(80, 80, 80), 1.5))
        painter.drawPath(up_arrow)
        painter.drawPath(down_arrow)
        painter.drawPath(left_arrow)
        painter.drawPath(right_arrow)
        
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
    
    @staticmethod
    def create_binarize_icon() -> QIcon:
        """Create a binarize icon (square wave representing binary signal)"""
        pixmap = QPixmap(FOLDER_ICON_SIZE, FOLDER_ICON_SIZE)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw square wave (smoothed signal)
        painter.setPen(QPen(QColor(100, 200, 255), 3))
        square_wave = QPainterPath()
        square_wave.moveTo(8, 40)
        square_wave.lineTo(8, 24)
        square_wave.lineTo(18, 24)
        square_wave.lineTo(18, 40)
        square_wave.lineTo(28, 40)
        square_wave.lineTo(28, 24)
        square_wave.lineTo(38, 24)
        square_wave.lineTo(38, 40)
        square_wave.lineTo(48, 40)
        square_wave.lineTo(48, 24)
        square_wave.lineTo(56, 24)
        painter.drawPath(square_wave)
        
        # Draw small arrow/indicator in top right
        painter.setPen(QPen(COLOR_GOLD, 2))
        painter.setBrush(COLOR_GOLD)
        arrow = QPainterPath()
        arrow.moveTo(52, 8)
        arrow.lineTo(48, 12)
        arrow.lineTo(56, 12)
        arrow.closeSubpath()
        painter.drawPath(arrow)
        
        painter.end()
        return QIcon(pixmap)

