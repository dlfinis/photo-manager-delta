#!/usr/bin/env python3
"""
Photo Consolidation System
============================================

Features:
- Advanced duplicate detection (exact, visual, burst)
- Organization by existing albums
- Google Takeout processing
- RAW file management
- EXIF date correction

Usage:
    python photo_consolidator.py --source ./photos --destination ./consolidated

Dependencies:
    sudo apt install dcraw imagemagick exiv2
    pip install pillow imagededup opencv-python scikit-learn tqdm
"""

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime

from duplicate_detector import AdvancedDuplicateDetector
from file_manager import FileManager
from photo_organizer import PhotoOrganizer
from utils import configure_logging, validate_dependencies, load_config

class PhotoConsolidator:
    def __init__(self, source: Path, destination: Path, temp_dir: Path, config: dict = None):
        self.source = source.resolve()
        self.destination = destination.resolve()
        self.temp_dir = temp_dir.resolve()
        
        # Load configuration if not provided
        if config is None:
            config = load_config()

        # System components
        self.file_manager = FileManager(self.source, self.destination, self.temp_dir, config)
        self.duplicate_detector = AdvancedDuplicateDetector(config)
        self.photo_organizer = PhotoOrganizer(self.destination, config)

        # Global statistics
        self.stats = {
            'start': datetime.now(),
            'files_processed': 0,
            'duplicates_removed': 0,
            'files_moved': 0,
            'errors': 0
        }

        self.logger = logging.getLogger(__name__)

    def validate_configuration(self):
        """Validate initial configuration"""
        self.logger.info("🔍 Validating configuration...")

        # Validate folders
        if not self.source.exists():
            raise FileNotFoundError(f"Source folder does not exist: {self.source}")

        if self.source == self.destination:
            raise ValueError("Source and destination folders cannot be the same")

        # Create necessary folders
        self.destination.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # Validate dependencies
        validate_dependencies()

        self.logger.info("✅ Configuration valid")

    def execute_consolidation(self, dry_run=False, skip_visual=False,
                             visual_threshold=0.85, temporal_threshold=5):
        """Execute the complete consolidation process"""

        try:
            self.logger.info("🚀 Starting photo consolidation...")
            self.logger.info(f"📂 Source: {self.source}")
            self.logger.info(f"📂 Destination: {self.destination}")

            # 1. Validate configuration
            self.validate_configuration()

            # 2. Detect existing albums
            self.logger.info("🖼️ Detecting existing albums...")
            albums = self.photo_organizer.detect_existing_albums()

            # 3. Collect files
            self.logger.info("📁 Collecting files...")
            files = self.file_manager.collect_files()
            self.stats['files_processed'] = len(files)

            if not files:
                self.logger.warning("⚠️ No files found to process")
                return

            # 4. Configure duplicate detector
            self.duplicate_detector.configure(
                visual_threshold=visual_threshold,
                temporal_threshold=temporal_threshold
            )

            # 5. Remove duplicates
            self.logger.info("🔍 Removing duplicates...")
            unique_files = self.duplicate_detector.remove_duplicates(
                files,
                self.file_manager.get_creation_time,
                skip_visual=skip_visual
            )

            duplicates_removed = len(files) - len(unique_files)
            self.stats['duplicates_removed'] = duplicates_removed
            self.logger.info(f"✅ Duplicates removed: {duplicates_removed}")

            # 6. Plan moves
            self.logger.info("📋 Planning moves...")
            moves = self.photo_organizer.plan_moves(
                unique_files,
                albums,
                self.file_manager.get_creation_time
            )

            # 7. Generate report
            self.logger.info("📄 Generating report...")
            self.generate_report(moves)

            # 8. Execute moves
            if dry_run:
                self.logger.info("📝 Dry run mode - no files will be moved")
            else:
                if self.confirm_execution(len(moves)):
                    self.logger.info("📦 Executing moves...")
                    files_moved = self.file_manager.execute_moves(moves)
                    self.stats['files_moved'] = files_moved
                    self.logger.info("✅ Consolidation completed successfully")
                else:
                    self.logger.info("❌ Consolidation cancelled by user")

        except Exception as e:
            self.logger.error(f"❌ Error during consolidation: {e}")
            self.stats['errors'] += 1
            raise

        finally:
            self.show_final_summary()

    def confirm_execution(self, num_moves):
        """Request user confirmation"""
        print(f"\n📊 Summary:")
        print(f"   - Files to move: {num_moves}")
        print(f"   - Duplicates removed: {self.stats['duplicates_removed']}")

        response = input("\nProceed with consolidation? (y/N): ").strip().lower()
        return response in ['y', 'yes']

    def generate_report(self, moves):
        """Generate detailed report"""
        report_path = self.destination / "consolidation_report.txt"

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("PHOTO CONSOLIDATION REPORT\n")
            f.write("=" * 50 + "\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Source: {self.source}\n")
            f.write(f"Destination: {self.destination}\n\n")

            f.write("STATISTICS:\n")
            f.write("-" * 20 + "\n")
            f.write(f"Files processed: {self.stats['files_processed']}\n")
            f.write(f"Duplicates removed: {self.stats['duplicates_removed']}\n")
            f.write(f"Files to move: {len(moves)}\n\n")

            # Detector statistics
            detector_stats = self.duplicate_detector.get_stats()
            f.write("DUPLICATES BY TYPE:\n")
            f.write("-" * 20 + "\n")
            for type, count in detector_stats.items():
                f.write(f"{type}: {count}\n")
            f.write("\n")

            # Organizer statistics
            organizer_stats = self.photo_organizer.get_stats()
            f.write("ORGANIZATION:\n")
            f.write("-" * 20 + "\n")
            for category, count in organizer_stats.items():
                f.write(f"{category}: {count}\n")
            f.write("\n")

            f.write("PLANNED MOVES:\n")
            f.write("-" * 30 + "\n")
            for source, destination, timestamp in moves:
                date = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"{source} → {destination} [{date}]\n")

        self.logger.info(f"📄 Report saved: {report_path}")

    def show_final_summary(self):
        """Show final execution summary"""
        duration = datetime.now() - self.stats['start']

        print(f"\n📊 FINAL SUMMARY")
        print(f"=" * 40)
        print(f"⏱️  Duration: {duration}")
        print(f"📁 Files processed: {self.stats['files_processed']}")
        print(f"🗑️  Duplicates removed: {self.stats['duplicates_removed']}")
        print(f"📦 Files moved: {self.stats['files_moved']}")
        print(f"❌ Errors: {self.stats['errors']}")

def main():
    parser = argparse.ArgumentParser(
        description="Photo Consolidation System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --source ./photos --destination ./consolidated
  %(prog)s --source ./takeout --destination ./consolidated --dry-run
  %(prog)s --source ./photos --destination ./consolidated --skip-visual --verbose
        """
    )

    parser.add_argument("--source", required=True, type=Path,
                       help="Source folder with photos to consolidate")
    parser.add_argument("--destination", required=True, type=Path,
                       help="Destination folder for consolidated photos")
    parser.add_argument("--temp", type=Path, default=Path("/tmp/consolidation"),
                       help="Temporary folder for processing")

    parser.add_argument("--dry-run", action="store_true",
                       help="Dry run, do not move files")
    parser.add_argument("--skip-visual", action="store_true",
                       help="Skip visual duplicate detection")

    parser.add_argument("--visual-threshold", type=float, default=0.85,
                       help="Visual similarity threshold (0.0-1.0)")
    parser.add_argument("--temporal-threshold", type=int, default=5,
                       help="Maximum seconds to consider a burst")

    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose mode")
    parser.add_argument("--debug", action="store_true",
                       help="Debug mode")

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else (logging.INFO if args.verbose else logging.WARNING)
    configure_logging(log_level)

    try:
        # Load configuration
        config = load_config()
        
        # Create and execute consolidator
        consolidator = PhotoConsolidator(args.source, args.destination, args.temp, config)
        consolidator.execute_consolidation(
            dry_run=args.dry_run,
            skip_visual=args.skip_visual,
            visual_threshold=args.visual_threshold,
            temporal_threshold=args.temporal_threshold
        )

    except KeyboardInterrupt:
        print("\n❌ Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()