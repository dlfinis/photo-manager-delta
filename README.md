# Photo Manager Delta - Local Photo Server Consolidation Tool

![CLI Workflow](https://img.shields.io/badge/CLI-Python3.8+-blue?logo=python)
![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS-lightgrey)

A robust toolkit for organizing and deduplicating photo collections from local servers or Google Takeout exports. Designed for photography enthusiasts managing your personal archives.

## ✨ Features
- **Advanced Deduplication** - Perceptual hashing and CNN-based duplicate detection
- **Metadata Preservation** - Maintains EXIF/XMP data during processing
- **RAW Support** - Handles CR2, NEF, ARW and other RAW formats via dcraw
- **Smart Grouping** - Time-based and content-based photo organization
- **Cross-Platform** - Works with Linux/macOS server environments

## 🛠️ Installation
```bash
# Run installer with system dependencies
chmod +x install_deps.sh
./install_deps.sh [--venv]  # Optional virtual environment
```

## 🚀 Basic Usage
```bash
# Consolidate photos from multiple sources
python3 consolidator.py --source ~/takeout/ --destination /media/photo-server/

# Manual definitions
python consolidator.py \
    --source ./takeout/ \
    --destination /media/photo-server/ \
    --visual-threshold 0.90 \
    --temporal-threshold 3 \
    --verbose
```

## ⚙️ Configuration
Create `config.yaml` for custom processing:
```yaml
processing:
  raw_conversion: true
  thumbnail_generation: 1024x768
  metadata_preservation: all
storage:
  hierarchy: %Y/%m-%B/%d-%A
  naming: {original_name}_{sha256sum}
```

## 📚 Supported Formats
| Category      | Formats                          |
|----------------------------------|
| RAW Images    | CR2, NEF, ARW, DNG, RW2         |
| Standard      | JPEG, PNG, WebP, HEIC           |
| Video         | MP4, MOV, AVI (metadata only)   |

## 📄 License
MIT License - See [LICENSE](LICENSE) for details
