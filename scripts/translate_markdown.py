"""
CLI Tool for Document Translation

Usage:
    # Single file
    python scripts/translate_markdown.py --input input.md --output output.md
    
    # Batch
    python scripts/translate_markdown.py --input-dir spanish/ --output-dir english/
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from translation.translate_document import DocumentTranslator


def translate_single_file(input_path, output_path, source_lang="es", target_lang="en"):
    """Translate a single file."""
    translator = DocumentTranslator()
    success = translator.translate_file(input_path, output_path, source_lang, target_lang)
    return success


def translate_directory(input_dir, output_dir, source_lang="es", target_lang="en"):
    """Translate all markdown files in directory."""
    input_path = Path(input_dir)
    markdown_files = list(input_path.glob("*.md"))
    
    if not markdown_files:
        print(f"❌ No markdown files found in {input_dir}")
        return False
    
    print(f"\n📁 Found {len(markdown_files)} file(s)")
    
    translator = DocumentTranslator()
    success_count = 0
    
    for i, input_file in enumerate(markdown_files, 1):
        print(f"\n{'='*60}")
        print(f"File {i}/{len(markdown_files)}: {input_file.name}")
        print(f"{'='*60}")
        
        output_file = Path(output_dir) / input_file.name
        
        if translator.translate_file(str(input_file), str(output_file), source_lang, target_lang):
            success_count += 1
    
    print(f"\n{'='*60}")
    print(f"✅ Batch Complete: {success_count}/{len(markdown_files)} successful")
    print(f"{'='*60}\n")
    
    return success_count == len(markdown_files)


def main():
    parser = argparse.ArgumentParser(description="Translate markdown documents")
    
    parser.add_argument("--input", help="Input file")
    parser.add_argument("--output", help="Output file")
    parser.add_argument("--input-dir", help="Input directory")
    parser.add_argument("--output-dir", help="Output directory")
    parser.add_argument("--source-lang", default="es", help="Source language (default: es)")
    parser.add_argument("--target-lang", default="en", help="Target language (default: en)")
    
    args = parser.parse_args()
    
    if args.input and args.output:
        success = translate_single_file(args.input, args.output, args.source_lang, args.target_lang)
        sys.exit(0 if success else 1)
    
    elif args.input_dir and args.output_dir:
        success = translate_directory(args.input_dir, args.output_dir, args.source_lang, args.target_lang)
        sys.exit(0 if success else 1)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()