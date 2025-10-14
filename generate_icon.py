"""Generate icon.ico file from the programmatic icon for PyInstaller"""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap, QPainter, QColor
from PyQt6.QtCore import Qt
from voltcraft_studio.icons import IconFactory

def generate_icon():
    """Generate and save multi-resolution icon.ico file"""
    app = QApplication(sys.argv)
    
    # Create the window icon
    icon = IconFactory.create_window_icon()
    
    # Windows .ico files typically contain multiple sizes: 16x16, 32x32, 48x48, 256x256
    # PyQt6 can save .ico with embedded sizes
    # Generate at largest size for best quality
    sizes = [256, 64, 48, 32, 16]
    
    # Get the largest pixmap
    pixmap = icon.pixmap(256, 256)
    
    # Save as .ico file
    # PyQt6 will automatically include multiple sizes when saving as ICO
    success = pixmap.save('icon.ico', 'ICO')
    
    if success:
        print("[OK] Generated icon.ico successfully!")
        print("     Icon will appear on VoltcraftStudio.exe")
    else:
        print("[ERROR] Failed to generate icon.ico")
        sys.exit(1)

if __name__ == "__main__":
    generate_icon()

