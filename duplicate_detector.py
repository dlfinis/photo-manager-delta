"""
Advanced Duplicate Detector
=============================

Detects multiple types of duplicates:
- Exact (binary hash)
- Content (same image, different compression)
- Visual (perceptual similarity)
- Burst (temporal sequence)
"""

import hashlib
import logging
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Tuple

import cv2
import numpy as np
from PIL import Image, ImageStat
import imagehash
from imagededup.methods import PHash, DHash, AHash
from tqdm import tqdm

class AdvancedDuplicateDetector:
    def __init__(self, config: dict = None):
        self.logger = logging.getLogger(__name__)

        # Load configuration if not provided
        if config is None:
            from utils import load_config
            config = load_config()
        
        self.config = config

        # Perceptual hash algorithms
        self.phasher = PHash()
        self.dhasher = DHash()
        self.ahasher = AHash()

        # Configuration - use defaults from config if available
        processing_config = config.get('processing', {})
        self.visual_threshold = processing_config.get('visual_threshold', 0.85)
        self.temporal_threshold = processing_config.get('temporal_threshold', 5)

        # Statistics
        self.stats = {
            'exact_duplicates': 0,
            'content_duplicates': 0,
            'visual_duplicates': 0,
            'burst_duplicates': 0,
            'opencv_duplicates': 0
        }

    def configure(self, visual_threshold=0.85, temporal_threshold=5):
        """Configure detection thresholds"""
        self.visual_threshold = visual_threshold
        self.temporal_threshold = temporal_threshold
        self.logger.info(f"🎯 Thresholds: visual={visual_threshold}, temporal={temporal_threshold}s")

    def calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of the entire file"""
        h = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            return h.hexdigest()
        except Exception as e:
            self.logger.debug(f"Error calculating hash of {file_path}: {e}")
            return ""

    def calculate_content_hash(self, file_path: Path) -> str:
        """Hash of visual content, ignoring metadata"""
        try:
            with Image.open(file_path) as img:
                # Normalize image
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img = img.resize((256, 256), Image.Resampling.LANCZOS)

                # Pixel hash
                return hashlib.md5(img.tobytes()).hexdigest()
        except Exception as e:
            self.logger.debug(f"Error calculating content hash of {file_path}: {e}")
            return ""

    def calculate_perceptual_hashes(self, file_path: Path) -> Dict[str, str]:
        """Calculate multiple perceptual hashes"""
        hashes = {}
        try:
            # imagededup hashes
            hashes['phash'] = self.phasher.encode_image(image_file=str(file_path))
            hashes['dhash'] = self.dhasher.encode_image(image_file=str(file_path))
            hashes['ahash'] = self.ahasher.encode_image(image_file=str(file_path))

            # Additional hashes with imagehash
            with Image.open(file_path) as img:
                hashes['whash'] = str(imagehash.whash(img))
                hashes['colorhash'] = str(imagehash.colorhash(img))

        except Exception as e:
            self.logger.debug(f"Error calculating perceptual hashes of {file_path}: {e}")

        return hashes

    def calculate_features(self, file_path: Path) -> Dict:
        """Extract image features"""
        features = {}
        try:
            with Image.open(file_path) as img:
                features['width'] = img.width
                features['height'] = img.height
                features['aspect'] = img.width / img.height
                features['pixels'] = img.width * img.height

                # Color statistics
                if img.mode == 'RGB':
                    stat = ImageStat.Stat(img)
                    features['brightness'] = sum(stat.mean) / 3
                    features['contrast'] = sum(stat.stddev) / 3

        except Exception as e:
            self.logger.debug(f"Error calculating features of {file_path}: {e}")

        return features

    def detect_exact_duplicates(self, files_data: List[Dict]) -> Dict:
        """Detect exact duplicates by binary hash"""
        self.logger.info("📋 Detecting exact duplicates...")

        hash_groups = defaultdict(list)
        for data in files_data:
            h = data['binary_hash']
            if h:
                hash_groups[h].append(data)

        duplicates = {}
        for h, group in hash_groups.items():
            if len(group) > 1:
                best = self.select_best_file(group)
                for data in group:
                    if data != best:
                        file_str = str(data['path'])
                        duplicates[file_str] = [(str(best['path']), 1.0, 'exact')]
                        self.stats['exact_duplicates'] += 1

        return duplicates

    def detect_content_duplicates(self, files_data: List[Dict]) -> Dict:
        """Detect duplicates by visual content"""
        self.logger.info("🎨 Detecting content duplicates...")

        content_groups = defaultdict(list)
        for data in files_data:
            h = data['content_hash']
            if h:
                content_groups[h].append(data)

        duplicates = {}
        for h, group in content_groups.items():
            if len(group) > 1:
                best = self.select_best_file(group)
                for data in group:
                    if data != best:
                        file_str = str(data['path'])
                        duplicates[file_str] = [(str(best['path']), 1.0, 'content')]
                        self.stats['content_duplicates'] += 1

        return duplicates

    def detect_visual_duplicates(self, files_data: List[Dict]) -> Dict:
        """Detect visual duplicates using perceptual hashes"""
        self.logger.info("👁️ Detecting visual duplicates...")

        duplicates = {}

        for i, data1 in enumerate(tqdm(files_data, desc="Comparing")):
            matches = []

            for j, data2 in enumerate(files_data[i+1:], i+1):
                similarity = self.calculate_perceptual_similarity(
                    data1['perceptual_hashes'],
                    data2['perceptual_hashes']
                )

                if similarity > self.visual_threshold:
                    matches.append((str(data2['path']), similarity, 'visual'))

            if matches:
                duplicates[str(data1['path'])] = matches
                self.stats['visual_duplicates'] += len(matches)

        return duplicates

    def calculate_perceptual_similarity(self, hashes1: Dict, hashes2: Dict) -> float:
        """Calculate average similarity between perceptual hashes"""
        similarities = []

        # PHash (more important)
        if 'phash' in hashes1 and 'phash' in hashes2:
            try:
                dist = bin(int(hashes1['phash'], 16) ^ int(hashes2['phash'], 16)).count('1')
                sim = 1.0 - (dist / 64.0)
                similarities.append(sim * 2)  # Double weight for PHash
            except:
                pass

        # Other hashes
        for tipo in ['dhash', 'ahash', 'whash', 'colorhash']:
            if tipo in hashes1 and tipo in hashes2:
                try:
                    if tipo in ['whash', 'colorhash']:
                        hash1 = imagehash.hex_to_hash(hashes1[tipo])
                        hash2 = imagehash.hex_to_hash(hashes2[tipo])
                        dist = hash1 - hash2
                        sim = 1.0 - (dist / 64.0)
                    else:
                        sim = 1.0 if hashes1[tipo] == hashes2[tipo] else 0.0

                    similarities.append(sim)
                except:
                    continue

        return sum(similarities) / len(similarities) if similarities else 0.0

    def detect_burst_duplicates(self, files_data: List[Dict]) -> Dict:
        """Detect duplicates in photo bursts"""
        self.logger.info("📸 Detecting burst duplicates...")

        # Group by time
        temporal_groups = self.group_by_time(files_data)
        duplicates = {}

        for group in temporal_groups:
            if len(group) <= 1:
                continue

            # Analyze similarities within the group
            for i, data1 in enumerate(group):
                matches = []

                for j, data2 in enumerate(group[i+1:], i+1):
                    sim_visual = self.calculate_perceptual_similarity(
                        data1['perceptual_hashes'],
                        data2['perceptual_hashes']
                    )

                    sim_features = self.calculate_feature_similarity(
                        data1['features'],
                        data2['features']
                    )

                    total_similarity = (sim_visual * 0.7) + (sim_features * 0.3)

                    if total_similarity > 0.8:
                        matches.append((str(data2['path']), total_similarity, 'burst'))

                if matches:
                    duplicates[str(data1['path'])] = matches
                    self.stats['burst_duplicates'] += len(matches)

        return duplicates

    def group_by_time(self, files_data: List[Dict]) -> List[List[Dict]]:
        """Group files by temporal proximity"""
        sorted_files = sorted(files_data, key=lambda x: x['timestamp'])

        groups = []
        current_group = [sorted_files[0]]

        for i in range(1, len(sorted_files)):
            current_file = sorted_files[i]
            previous_file = sorted_files[i-1]

            difference = abs(current_file['timestamp'] - previous_file['timestamp'])

            if difference <= self.temporal_threshold:
                current_group.append(current_file)
            else:
                if len(current_group) > 1:
                    groups.append(current_group)
                current_group = [current_file]

        if len(current_group) > 1:
            groups.append(current_group)

        return groups

    def calculate_feature_similarity(self, features1: Dict, features2: Dict) -> float:
        """Calculate similarity based on features"""
        if not features1 or not features2:
            return 0.0

        similarities = []

        # Aspect
        if 'aspect' in features1 and 'aspect' in features2:
            diff = abs(features1['aspect'] - features2['aspect'])
            sim = max(0, 1.0 - diff)
            similarities.append(sim)

        # Brightness
        if 'brightness' in features1 and 'brightness' in features2:
            diff = abs(features1['brightness'] - features2['brightness']) / 255.0
            sim = max(0, 1.0 - diff)
            similarities.append(sim)

        return sum(similarities) / len(similarities) if similarities else 0.0

    def select_best_file(self, candidates: List[Dict]) -> Dict:
        """Choose the best file from a group"""
        def score_file(data):
            score = 0

            # File size
            score += data['size']

            # Resolution
            if 'features' in data and 'pixels' in data['features']:
                score += data['features']['pixels'] * 0.001

            # Extension
            ext = data['path'].suffix.lower()
            if ext in ['.dng', '.arw', '.nef', '.cr2']:
                score += 10000  # RAW maximum priority
            elif ext in ['.jpg', '.jpeg']:
                score += 1000
            elif ext == '.png':
                score += 500

            return score

        return max(candidates, key=score_file)

    def remove_duplicates(self, files: List[Path], get_timestamp_func, skip_visual=False) -> List[Path]:
        """Complete duplicate removal process"""

        # Prepare data
        self.logger.info("📋 Preparing data for analysis...")
        files_data = []

        for file in tqdm(files, desc="Analyzing files"):
            try:
                data = {
                    'path': file,
                    'timestamp': get_timestamp_func(file),
                    'size': file.stat().st_size,
                    'binary_hash': self.calculate_file_hash(file),
                    'content_hash': self.calculate_content_hash(file),
                    'perceptual_hashes': self.calculate_perceptual_hashes(file),
                    'features': self.calculate_features(file)
                }
                files_data.append(data)
            except Exception as e:
                self.logger.error(f"Error processing {file}: {e}")

        # Detect duplicates
        all_duplicates = {}

        # 1. Exact duplicates
        exact_duplicates = self.detect_exact_duplicates(files_data)
        all_duplicates.update(exact_duplicates)

        # 2. Content duplicates
        content_duplicates = self.detect_content_duplicates(files_data)
        all_duplicates.update(content_duplicates)

        # 3. Visual duplicates (optional)
        if not skip_visual:
            visual_duplicates = self.detect_visual_duplicates(files_data)
            all_duplicates.update(visual_duplicates)

            # 4. Burst duplicates
            burst_duplicates = self.detect_burst_duplicates(files_data)
            all_duplicates.update(burst_duplicates)

        # Process duplicates
        files_to_remove = set()
        for original_file, matches in all_duplicates.items():
            for match_path, similarity, tipo in matches:
                files_to_remove.add(Path(match_path))

        # Return unique files
        unique_files = [file for file in files if file not in files_to_remove]

        self.logger.info(f"✅ Unique files: {len(unique_files)} of {len(files)}")
        return unique_files

    def get_stats(self) -> Dict[str, int]:
        """Return duplicate statistics"""
        return self.stats.copy()