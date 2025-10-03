"""
System Utilities
====================

Helper functions and configuration.
"""

import logging
import subprocess
import sys
from pathlib import Path
import yaml

def configure_logging(level=logging.INFO):
    """Configure logging system"""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('consolidation.log', encoding='utf-8')
        ]
    )

def validate_dependencies():
    """Validate that dependencies are installed"""
    logger = logging.getLogger(__name__)

    # Check dcraw
    try:
        subprocess.run(["dcraw", "-v"], capture_output=True, check=True)
        logger.debug("✅ dcraw available")
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.warning("⚠️ dcraw not available - RAW files will not be processed")

    # Check ImageMagick
    try:
        subprocess.run(["convert", "-version"], capture_output=True, check=True)
        logger.debug("✅ ImageMagick available")
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.warning("⚠️ ImageMagick not available")

    # Check Python libraries
    try:
        import PIL
        logger.debug("✅ Pillow available")
    except ImportError:
        logger.error("❌ Pillow not available - install with: pip install pillow")
        sys.exit(1)

    try:
        import imagededup
        logger.debug("✅ imagededup available")
    except ImportError:
        logger.warning("⚠️ imagededup not available - limited visual detection")

    try:
        import cv2
        logger.debug("✅ OpenCV available")
    except ImportError:
        logger.warning("⚠️ OpenCV not available - limited advanced detection")

def show_installation_help():
    """Show help for installing dependencies"""
    print("""
🛠️ DEPENDENCY INSTALLATION

System (Ubuntu/Debian):
    sudo apt update
    sudo apt install -y dcraw imagemagick exiv2 python3-pip

Python:
    pip install pillow imagededup opencv-python scikit-learn tqdm

Verification:
    dcraw -v
    convert -version
    python -c "import PIL, imagededup, cv2; print('✅ All installed')"
    """)

def load_config(config_path: Path = None) -> dict:
    """Load configuration from YAML file with defaults"""
    if config_path is None:
        config_path = Path("config.yaml")
    
    config = {}
    
    # Default configuration
    config['processing'] = {
        'raw_conversion': True,
        'thumbnail_generation': '1024x768',
        'metadata_preservation': 'all'
    }
    config['storage'] = {
        'hierarchy': '%Y/%m-%B/%d-%A',
        'naming': '{original_name}_{sha256sum}'
    }
    
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                file_config = yaml.safe_load(f)
                if file_config:
                    # Merge file config with defaults (file config takes precedence)
                    for section in ['processing', 'storage']:
                        if section in file_config:
                            config[section].update(file_config[section])
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning(f"Could not load config from {config_path}: {e}")
    
    return config