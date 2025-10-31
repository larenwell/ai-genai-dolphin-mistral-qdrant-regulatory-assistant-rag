#!/usr/bin/env python3
"""
Duplicate PDF Detector for Regulatory Documents

This script analyzes the normativa_analysis_report.xlsx file to identify duplicate PDF files
based on filename, size_mb, page_count, and title. It then organizes unique files into
the data/uniques folder and generates a comprehensive Excel report.

Author: AI Assistant
Date: 2024
"""

import os
import sys
import shutil
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime
import hashlib

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))


class DuplicateDetector:
    def __init__(self, analysis_report_path: str = "output/analysis/normativa_analysis_report.xlsx"):
        self.analysis_report_path = Path(analysis_report_path)
        self.data_folder = Path("data/normativa")
        self.uniques_folder = Path("data/uniques")
        self.results = []
        self.duplicates = []
        self.uniques = []
        
    def load_analysis_report(self) -> pd.DataFrame:
        """Load the PDF analysis report Excel file"""
        try:
            if not self.analysis_report_path.exists():
                raise FileNotFoundError(f"Analysis report not found: {self.analysis_report_path}")
            
            print(f"📊 Loading analysis report: {self.analysis_report_path}")
            df = pd.read_excel(self.analysis_report_path, sheet_name='Detailed Analysis')
            print(f"✅ Loaded {len(df)} records from analysis report")
            return df
        except Exception as e:
            print(f"❌ Error loading analysis report: {e}")
            return pd.DataFrame()
    
    def identify_duplicates(self, df: pd.DataFrame) -> Tuple[List[Dict], List[Dict]]:
        """Identify duplicate files based on multiple criteria"""
        print("\n🔍 Identifying duplicate files...")
        
        # Create a composite key for duplicate detection
        df['duplicate_key'] = df.apply(
            lambda row: f"{row['filename']}_{row['size_mb']}_{row['page_count']}_{row['title']}", 
            axis=1
        )
        
        # Find duplicates
        duplicate_groups = df.groupby('duplicate_key').filter(lambda x: len(x) > 1)
        unique_groups = df.groupby('duplicate_key').filter(lambda x: len(x) == 1)
        
        # Process duplicates
        duplicates = []
        for key, group in df.groupby('duplicate_key'):
            if len(group) > 1:
                # Sort by folder path to prioritize certain locations
                group_sorted = group.sort_values('folder')
                primary = group_sorted.iloc[0]  # First occurrence is primary
                duplicates_group = []
                
                for idx, row in group_sorted.iterrows():
                    duplicate_info = {
                        'filename': row['filename'],
                        'folder': row['folder'],
                        'size_mb': row['size_mb'],
                        'page_count': row['page_count'],
                        'title': row['title'],
                        'file_path': row['file_path'],
                        'duplicate_key': key,
                        'is_primary': (row.name == primary.name),
                        'duplicate_count': len(group)
                    }
                    duplicates_group.append(duplicate_info)
                
                duplicates.extend(duplicates_group)
        
        # Process uniques
        uniques = []
        for idx, row in unique_groups.iterrows():
            unique_info = {
                'filename': row['filename'],
                'folder': row['folder'],
                'size_mb': row['size_mb'],
                'page_count': row['page_count'],
                'title': row['title'],
                'file_path': row['file_path'],
                'duplicate_key': row['duplicate_key'],
                'is_primary': True,
                'duplicate_count': 1
            }
            uniques.append(unique_info)
        
        print(f"✅ Found {len(duplicates)} duplicate files in {len(set([d['duplicate_key'] for d in duplicates]))} groups")
        print(f"✅ Found {len(uniques)} unique files")
        
        return duplicates, uniques
    
    def organize_unique_files(self, uniques: List[Dict]) -> None:
        """Copy unique files to the data/uniques folder"""
        print(f"\n📁 Organizing unique files to {self.uniques_folder}...")
        
        # Create uniques folder if it doesn't exist
        self.uniques_folder.mkdir(parents=True, exist_ok=True)
        
        # Clear existing files in uniques folder
        for file in self.uniques_folder.glob("*"):
            if file.is_file():
                file.unlink()
        
        copied_count = 0
        errors = []
        
        for unique in uniques:
            try:
                # Construct proper source path using folder and filename
                if unique['folder'] == '.':
                    # Files in root of data/normativa
                    source_path = self.data_folder / unique['filename']
                else:
                    # Files in subfolders
                    source_path = self.data_folder / unique['folder'] / unique['filename']
                
                if source_path.exists():
                    # Create destination path
                    dest_path = self.uniques_folder / unique['filename']
                    
                    # Handle filename conflicts by adding folder prefix
                    if dest_path.exists():
                        folder_prefix = unique['folder'].replace('/', '_').replace(' ', '_')
                        if folder_prefix == '.':
                            folder_prefix = 'root'
                        dest_path = self.uniques_folder / f"{folder_prefix}_{unique['filename']}"
                    
                    # Copy file
                    shutil.copy2(source_path, dest_path)
                    copied_count += 1
                    
                    # Update the unique record with new path
                    unique['uniques_path'] = str(dest_path)
                    unique['source_path'] = str(source_path)
                else:
                    errors.append(f"Source file not found: {source_path}")
            except Exception as e:
                errors.append(f"Error copying {unique['filename']}: {e}")
        
        print(f"✅ Successfully copied {copied_count} unique files")
        if errors:
            print(f"⚠️  {len(errors)} errors occurred during copying")
            for error in errors[:5]:  # Show first 5 errors
                print(f"   - {error}")
    
    def generate_duplicate_report(self, duplicates: List[Dict], uniques: List[Dict]) -> str:
        """Generate comprehensive Excel report of duplicates and uniques"""
        print("\n📋 Generating duplicate analysis report...")
        
        # Create output directory
        output_dir = Path("output/analysis")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / "duplicate_analysis_report.xlsx"
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # Duplicates sheet
            if duplicates:
                duplicates_df = pd.DataFrame(duplicates)
                duplicates_df.to_excel(writer, sheet_name='Duplicates', index=False)
            
            # Uniques sheet
            if uniques:
                uniques_df = pd.DataFrame(uniques)
                uniques_df.to_excel(writer, sheet_name='Uniques', index=False)
            
            # Summary sheet
            self._create_summary_sheet(duplicates, uniques, writer)
            
            # Duplicate groups sheet
            if duplicates:
                self._create_duplicate_groups_sheet(duplicates, writer)
        
        print(f"✅ Duplicate analysis report generated: {output_file}")
        return str(output_file)
    
    def _create_summary_sheet(self, duplicates: List[Dict], uniques: List[Dict], writer: pd.ExcelWriter):
        """Create summary sheet with statistics"""
        summary_data = {
            'Metric': [
                'Total Files Analyzed',
                'Unique Files',
                'Duplicate Files',
                'Duplicate Groups',
                'Total Size (MB)',
                'Unique Size (MB)',
                'Duplicate Size (MB)',
                'Space Saved (MB)',
                'Duplication Rate (%)'
            ],
            'Value': [
                len(duplicates) + len(uniques),
                len(uniques),
                len(duplicates),
                len(set([d['duplicate_key'] for d in duplicates])),
                sum(d.get('size_mb', 0) for d in duplicates + uniques),
                sum(d.get('size_mb', 0) for d in uniques),
                sum(d.get('size_mb', 0) for d in duplicates),
                sum(d.get('size_mb', 0) for d in duplicates) - sum(d.get('size_mb', 0) for d in [d for d in duplicates if d['is_primary']]),
                round((len(duplicates) / (len(duplicates) + len(uniques))) * 100, 2) if (len(duplicates) + len(uniques)) > 0 else 0
            ]
        }
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
    
    def _create_duplicate_groups_sheet(self, duplicates: List[Dict], writer: pd.ExcelWriter):
        """Create sheet showing duplicate groups"""
        # Group duplicates by duplicate_key
        duplicate_groups = {}
        for duplicate in duplicates:
            key = duplicate['duplicate_key']
            if key not in duplicate_groups:
                duplicate_groups[key] = []
            duplicate_groups[key].append(duplicate)
        
        # Create groups data
        groups_data = []
        for key, group in duplicate_groups.items():
            primary = next(d for d in group if d['is_primary'])
            duplicates = [d for d in group if not d['is_primary']]
            
            groups_data.append({
                'Duplicate Group': key,
                'Primary File': primary['filename'],
                'Primary Location': primary['folder'],
                'File Size (MB)': primary['size_mb'],
                'Page Count': primary['page_count'],
                'Title': primary['title'],
                'Duplicate Count': len(duplicates),
                'Duplicate Locations': '; '.join([d['folder'] for d in duplicates])
            })
        
        groups_df = pd.DataFrame(groups_data)
        groups_df.to_excel(writer, sheet_name='Duplicate Groups', index=False)
    
    def run_analysis(self) -> Dict[str, Any]:
        """Run the complete duplicate detection analysis"""
        print("🔍 Duplicate PDF Detector - Regulatory Documents Analysis")
        print("=" * 60)
        
        # Load analysis report
        df = self.load_analysis_report()
        if df.empty:
            return {"error": "Failed to load analysis report"}
        
        # Identify duplicates and uniques
        duplicates, uniques = self.identify_duplicates(df)
        
        # Organize unique files
        self.organize_unique_files(uniques)
        
        # Generate report
        report_path = self.generate_duplicate_report(duplicates, uniques)
        
        # Return results
        return {
            "total_files": len(duplicates) + len(uniques),
            "unique_files": len(uniques),
            "duplicate_files": len(duplicates),
            "duplicate_groups": len(set([d['duplicate_key'] for d in duplicates])),
            "report_path": report_path,
            "uniques_folder": str(self.uniques_folder)
        }


def main():
    """Main function to run the duplicate detection analysis"""
    detector = DuplicateDetector()
    results = detector.run_analysis()
    
    if "error" in results:
        print(f"❌ Analysis failed: {results['error']}")
        return
    
    print("\n📈 Duplicate Analysis Summary:")
    print("-" * 40)
    print(f"📁 Total files analyzed: {results['total_files']}")
    print(f"✅ Unique files: {results['unique_files']}")
    print(f"🔄 Duplicate files: {results['duplicate_files']}")
    print(f"📊 Duplicate groups: {results['duplicate_groups']}")
    print(f"📋 Report generated: {results['report_path']}")
    print(f"📁 Unique files organized in: {results['uniques_folder']}")
    
    # Calculate space savings
    if results['duplicate_files'] > 0:
        print(f"💾 Space optimization: Duplicates identified for removal")
        print(f"📊 Duplication rate: {(results['duplicate_files'] / results['total_files']) * 100:.1f}%")


if __name__ == "__main__":
    main()
