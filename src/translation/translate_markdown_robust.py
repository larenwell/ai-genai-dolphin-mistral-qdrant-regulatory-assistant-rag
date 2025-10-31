"""
Robust CLI Tool for Document Translation with Resume Capability

Usage:
    # Single file
    python scripts/translate_markdown_robust.py --input input.md --output output.md
    
    # Batch with resume capability
    python scripts/translate_markdown_robust.py --input-dir spanish/ --output-dir english/ --resume
"""

import sys
import argparse
from pathlib import Path
import json
import time

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from translation.translate_document import DocumentTranslator


def get_translation_progress(input_dir, output_dir):
    """Get progress of translation by comparing input and output files."""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    if not output_path.exists():
        output_path.mkdir(parents=True, exist_ok=True)
        return [], []
    
    input_files = set(f.name for f in input_path.glob("*.md"))
    output_files = set(f.name for f in output_path.glob("*.md"))
    
    completed = list(output_files)
    remaining = list(input_files - output_files)
    
    return completed, remaining


def translate_single_file(input_path, output_path, source_lang="es", target_lang="en", timeout=60):
    """Translate a single file with timeout."""
    translator = DocumentTranslator(timeout_seconds=timeout)
    success = translator.translate_file(input_path, output_path, source_lang, target_lang)
    return success


def translate_directory_robust(input_dir, output_dir, source_lang="es", target_lang="en", 
                             timeout=60, resume=True, max_files=None):
    """Translate all markdown files in directory with robust error handling."""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    if not output_path.exists():
        output_path.mkdir(parents=True, exist_ok=True)
    
    # Get progress
    completed, remaining = get_translation_progress(input_dir, output_dir)
    
    if resume and completed:
        print(f"📊 Resume mode: {len(completed)} files already translated, {len(remaining)} remaining")
        markdown_files = [input_path / f for f in remaining]
    else:
        markdown_files = list(input_path.glob("*.md"))
    
    if not markdown_files:
        print(f"❌ No markdown files found in {input_dir}")
        return False
    
    if max_files:
        markdown_files = markdown_files[:max_files]
        print(f"🔢 Limiting to first {max_files} files")
    
    print(f"\n📁 Processing {len(markdown_files)} file(s)")
    
    translator = DocumentTranslator(timeout_seconds=timeout)
    success_count = 0
    failed_files = []
    
    for i, input_file in enumerate(markdown_files, 1):
        print(f"\n{'='*60}")
        print(f"File {i}/{len(markdown_files)}: {input_file.name}")
        print(f"{'='*60}")
        
        output_file = output_path / input_file.name
        
        try:
            if translator.translate_file(str(input_file), str(output_file), source_lang, target_lang):
                success_count += 1
                print(f"✅ Successfully translated: {input_file.name}")
            else:
                failed_files.append(input_file.name)
                print(f"❌ Failed to translate: {input_file.name}")
        except KeyboardInterrupt:
            print(f"\n⚠️ Interrupted by user. Progress saved.")
            print(f"✅ Completed: {success_count}/{i-1}")
            print(f"❌ Failed: {len(failed_files)}")
            if failed_files:
                print(f"Failed files: {', '.join(failed_files)}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error translating {input_file.name}: {e}")
            failed_files.append(input_file.name)
            continue
    
    print(f"\n{'='*60}")
    print(f"✅ Batch Complete: {success_count}/{len(markdown_files)} successful")
    if failed_files:
        print(f"❌ Failed files: {', '.join(failed_files)}")
    print(f"{'='*60}\n")
    
    return success_count == len(markdown_files)


def main():
    parser = argparse.ArgumentParser(description="Robust markdown document translator with resume capability")
    
    parser.add_argument("--input", help="Input file")
    parser.add_argument("--output", help="Output file")
    parser.add_argument("--input-dir", help="Input directory")
    parser.add_argument("--output-dir", help="Output directory")
    parser.add_argument("--source-lang", default="es", help="Source language (default: es)")
    parser.add_argument("--target-lang", default="en", help="Target language (default: en)")
    parser.add_argument("--timeout", type=int, default=60, help="Timeout in seconds (default: 60)")
    parser.add_argument("--resume", action="store_true", help="Resume from where it left off")
    parser.add_argument("--max-files", type=int, help="Maximum number of files to process")
    
    args = parser.parse_args()
    
    if args.input and args.output:
        success = translate_single_file(args.input, args.output, args.source_lang, args.target_lang, args.timeout)
        sys.exit(0 if success else 1)
    
    elif args.input_dir and args.output_dir:
        success = translate_directory_robust(
            args.input_dir, 
            args.output_dir, 
            args.source_lang, 
            args.target_lang,
            args.timeout,
            args.resume,
            args.max_files
        )
        sys.exit(0 if success else 1)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
