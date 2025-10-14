"""Generate icon.ico file from the programmatic icon for PyInstaller"""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap
from icons import IconFactory

def generate_icon():
    """Generate and save icon.ico file"""
    app = QApplication(sys.argv)
    
    # Create the window icon (64x64)
    icon = IconFactory.create_window_icon()
    
    # Get the pixmap from the icon
    pixmap = icon.pixmap(256, 256)  # Generate at 256x256 for high quality
    
    # Save as .ico file (contains multiple sizes)
    success = pixmap.save('icon.ico', 'ICO')
    
    if success:
        print("[OK] Generated icon.ico successfully!")
    else:
        print("[ERROR] Failed to generate icon.ico")
        sys.exit(1)

if __name__ == "__main__":
    generate_icon()

