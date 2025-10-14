# Building Voltcraft Studio

## Creating a Release

Automated builds are set up via GitHub Actions. To create a new release:

### 1. Tag a new version
```bash
git tag v1.0.0
git push origin v1.0.0
```

### 2. GitHub Actions will automatically:
- Build a portable Windows executable (`VoltcraftStudio.exe`)
- Create a GitHub Release with the tag
- Upload the .exe as a release asset

### 3. Download your release
Go to: `https://github.com/YOUR_USERNAME/voltcraft-studio/releases`

The executable will be named `VoltcraftStudio.exe` and will be ~50-100MB (includes Python, PyQt6, and all dependencies).

---

## Manual Local Build (Optional)

If you want to build locally:

### 1. Install PyInstaller
```bash
pip install pyinstaller
```

### 2. Generate the icon
```bash
python generate_icon.py
```

### 3. Build the executable
```bash
pyinstaller --clean --noconfirm build.spec
```

### 4. Find your executable
The .exe will be in `dist/VoltcraftStudio.exe`

---

## Build Configuration

- **`build.spec`** - PyInstaller configuration
- **`generate_icon.py`** - Creates `icon.ico` from programmatic icon
- **`.github/workflows/build-release.yml`** - Automated build workflow

### Customization

To change the build:
- Edit `build.spec` for PyInstaller options
- Edit `.github/workflows/build-release.yml` for CI/CD settings
- Hidden imports are configured in `build.spec` if you add new dependencies

---

## Troubleshooting

**Build fails with missing module:**
Add the module to `hiddenimports` in `build.spec`

**Icon doesn't show:**
Make sure `generate_icon.py` runs successfully before PyInstaller

**Exe is too large:**
PyInstaller bundles Python runtime + all dependencies. This is normal for portable executables.
Typical size: 60-100 MB

**OpenGL warnings:**
OpenGL acceleration is optional. The app will fall back to CPU rendering if unavailable.

