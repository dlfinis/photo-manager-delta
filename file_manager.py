"""
File Manager
=================

Handles file collection, movement and date management.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Tuple
import logging
from tqdm import tqdm

class FileManager:
    def __init__(self, source: Path, destination: Path, temp_dir: Path, config: dict = None):
        self.source = source
        self.destination = destination
        self.temp_dir = temp_dir
        self.logger = logging.getLogger(__name__)

        # Load configuration if not provided
        if config is None:
            from utils import load_config
            config = load_config()
        
        self.config = config

        # Supported extensions
        self.img_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tiff', '.tif'}
        self.raw_extensions = {'.dng', '.arw', '.nef', '.cr2', '.cr3', '.orf', '.rw2', '.raf'}
        self.all_extensions = self.img_extensions | self.raw_extensions

    def collect_files(self) -> List[Path]:
        """Collect all image files"""
        self.logger.info("📁 Collecting files...")

        files = []

        # Search in source
        for ext in self.all_extensions:
            files.extend(self.source.rglob(f"*{ext}"))
            files.extend(self.source.rglob(f"*{ext.upper()}"))

        # Filter only valid files
        files = [f for f in files if f.is_file() and f.stat().st_size > 0]

        self.logger.info(f"📁 Files found: {len(files)}")
        return files

    def get_creation_time(self, file_path: Path) -> float:
        """Get creation date from multiple sources"""

        # 1. Google Takeout JSON
        json_paths = [
            file_path.with_suffix(file_path.suffix + '.json'),
            file_path.with_suffix('.json'),
            file_path.parent / (file_path.stem + '.json')
        ]

        for json_path in json_paths:
            if json_path.exists():
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        meta = json.load(f)

                        # Different timestamp formats
                        for key in ['creationTime', 'photoTakenTime']:
                            if key in meta:
                                time_data = meta[key]
                                if isinstance(time_data, dict):
                                    ts = int(time_data.get('timestamp', 0))
                                elif isinstance(time_data, str):
                                    ts = int(time_data)
                                else:
                                    ts = int(time_data) if time_data else 0

                                if ts > 0:
                                    self.logger.debug(f"Date from JSON: {datetime.fromtimestamp(ts)}")
                                    return ts

                except Exception as e:
                    self.logger.debug(f"Error reading JSON {json_path}: {e}")

        # 2. EXIF data
        try:
            from PIL import Image, ExifTags
            with Image.open(file_path) as img:
                exif = img.getexif()
                if exif:
                    for tag_name in ["DateTimeOriginal", "DateTime", "DateTimeDigitized"]:
                        for tag, value in exif.items():
                            if ExifTags.TAGS.get(tag, tag) == tag_name and value:
                                try:
                                    dt = datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
                                    self.logger.debug(f"Date from EXIF ({tag_name}): {dt}")
                                    return dt.timestamp()
                                except ValueError:
                                    continue
        except Exception as e:
            self.logger.debug(f"Could not read EXIF from {file_path}: {e}")

        # 3. System date
        return file_path.stat().st_mtime

    def execute_moves(self, moves: List[Tuple[Path, Path, float]]) -> int:
        """Execute planned moves"""
        files_moved = 0

        for source_file, destination_file, timestamp in tqdm(moves, desc="Moving files"):
            try:
                # Create destination directory
                destination_file.parent.mkdir(parents=True, exist_ok=True)

                # Copy file preserving metadata
                shutil.copy2(source_file, destination_file)

                # Fix creation date
                os.utime(destination_file, (timestamp, timestamp))

                # Remove original if it's in source
                if self.source in source_file.parents:
                    source_file.unlink()

                files_moved += 1

            except Exception as e:
                self.logger.error(f"Error moving {source_file} → {destination_file}: {e}")

        return files_moved

    def convert_raw_to_jpg(self, raw_path: Path, jpg_path: Path) -> bool:
        """Convert RAW file to JPG for analysis"""
        try:
            # Check dcraw
            subprocess.run(["dcraw", "-v"], capture_output=True, check=True)

            # Convert
            cmd = ["dcraw", "-c", "-w", "-H", "1", "-q", "3", "-T", str(raw_path)]
            result = subprocess.run(cmd, capture_output=True, check=True)

            # Process with ImageMagick
            convert_cmd = [
                "convert", "-", "-strip", "-resize", "1024x1024>",
                "-quality", "85", str(jpg_path)
            ]
            subprocess.run(convert_cmd, input=result.stdout, check=True)

            return True

        except Exception as e:
            self.logger.debug(f"Error converting {raw_path}: {e}")
            return False