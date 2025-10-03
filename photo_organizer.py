"""
Photo Organizer
==================

Handles organization by albums and dates.
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Callable

class PhotoOrganizer:
    def __init__(self, destination: Path, config: dict = None):
        self.destination = destination
        self.logger = logging.getLogger(__name__)

        # Load configuration if not provided
        if config is None:
            from utils import load_config
            config = load_config()
        
        self.config = config

        # RAW extensions
        self.raw_extensions = {'.dng', '.arw', '.nef', '.cr2', '.cr3', '.orf', '.rw2', '.raf'}

        # Statistics
        self.stats = {
            'assigned_to_album': 0,
            'organized_by_date': 0,
            'raw_processed': 0
        }

    def detect_existing_albums(self) -> Dict[str, Path]:
        """Detect existing albums in destination folder"""
        albums = {}

        if not self.destination.exists():
            return albums

        for item in self.destination.iterdir():
            if item.is_dir() and item.name not in ['raw', 'temp', 'duplicates', '.git']:
                # Create name variants for matching
                original_name = item.name
                lower_name = original_name.lower()
                normalized_name = lower_name.replace('_', ' ').replace('-', ' ')

                # Add variants
                albums[lower_name] = item
                albums[normalized_name] = item

                # Add keywords
                words = normalized_name.split()
                for word in words:
                    if len(word) > 3:  # Only significant words
                        albums[word] = item

        album_names = set(item.name for item in albums.values())
        self.logger.info(f"🖼️ Albums detected: {album_names}")

        return albums

    def find_matching_album(self, file_path: Path, albums: Dict[str, Path]) -> Path:
        """Find matching album based on path"""
        path_str = str(file_path).lower()
        path_parts = [part.lower() for part in file_path.parts]

        # Search for exact matches
        for album_key, album_path in albums.items():
            if album_key in path_str:
                self.logger.debug(f"Match: {file_path} → {album_path.name}")
                return album_path

        # Search in path parts
        for album_key, album_path in albums.items():
            for part in path_parts:
                if album_key in part or part in album_key:
                    self.logger.debug(f"Partial match: {file_path} → {album_path.name}")
                    return album_path

        return None

    def plan_moves(self, files: List[Path], albums: Dict[str, Path],
                   get_timestamp_func: Callable) -> List[Tuple[Path, Path, float]]:
        """Plan where to move each file"""
        moves = []
        raw_dir = self.destination / "raw"

        for file in files:
            # Get timestamp
            timestamp = get_timestamp_func(file)
            date = datetime.fromtimestamp(timestamp)

            # Determine if it's RAW
            is_raw = file.suffix.lower() in self.raw_extensions

            # Search for matching album
            album_destination = self.find_matching_album(file, albums)

            if album_destination and not is_raw:
                # Assign to album
                final_destination = album_destination / file.name
                self.stats['assigned_to_album'] += 1

            elif is_raw:
                # Move to RAW folder
                year = str(date.year)
                final_destination = raw_dir / year / file.name
                self.stats['raw_processed'] += 1

            else:
                # Organize by date using configured hierarchy
                hierarchy = self.config.get('storage', {}).get('hierarchy', '%Y/%m-%B/%d-%A')
                date_path = date.strftime(hierarchy)
                final_destination = self.destination / date_path / file.name
                self.stats['organized_by_date'] += 1

            # Resolve name collisions
            final_destination = self.resolve_name_collision(final_destination)

            moves.append((file, final_destination, timestamp))

        return moves

    def resolve_name_collision(self, destination: Path) -> Path:
        """Resolve name collisions"""
        if not destination.exists():
            return destination

        counter = 1
        base = destination

        while destination.exists():
            stem = base.stem
            suffix = base.suffix
            destination = base.parent / f"{stem}_{counter}{suffix}"
            counter += 1

        return destination

    def get_stats(self) -> Dict[str, int]:
        """Return statistics"""
        return self.stats.copy()