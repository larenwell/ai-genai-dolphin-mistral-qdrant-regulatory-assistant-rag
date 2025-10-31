import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import datetime
import PyPDF2
import fitz  # PyMuPDF
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

load_dotenv(project_root / '.env')


class PDFAnalyzer:
    def __init__(self, data_folder: str = "data/normativa"):
        self.data_folder = Path(data_folder)
        self.results = []
        
    def get_file_size_mb(self, file_path: Path) -> float:
        """Get file size in MB"""
        try:
            size_bytes = file_path.stat().st_size
            return round(size_bytes / (1024 * 1024), 2)
        except Exception as e:
            print(f"Error getting file size for {file_path}: {e}")
            return 0.0
    
    def get_pdf_page_count_pypdf2(self, file_path: Path) -> Optional[int]:
        """Get page count using PyPDF2"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                return len(pdf_reader.pages)
        except Exception as e:
            print(f"PyPDF2 error for {file_path}: {e}")
            return None
    
    def get_pdf_page_count_pymupdf(self, file_path: Path) -> Optional[int]:
        """Get page count using PyMuPDF (more reliable)"""
        try:
            doc = fitz.open(file_path)
            page_count = len(doc)
            doc.close()
            return page_count
        except Exception as e:
            print(f"PyMuPDF error for {file_path}: {e}")
            return None
    
    def get_pdf_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract PDF metadata"""
        metadata = {
            'title': '',
            'author': '',
            'subject': '',
            'creator': '',
            'producer': '',
            'creation_date': '',
            'modification_date': ''
        }
        
        try:
            # Try PyPDF2 first
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                if pdf_reader.metadata:
                    pdf_metadata = pdf_reader.metadata
                    
                    # Convert ByteStringObject to string safely
                    def safe_convert(value):
                        if value is None:
                            return ''
                        try:
                            # Handle ByteStringObject and other non-serializable types
                            if hasattr(value, 'decode'):
                                return value.decode('utf-8', errors='ignore')
                            else:
                                return str(value)
                        except:
                            return str(value)
                    
                    metadata['title'] = safe_convert(pdf_metadata.get('/Title', ''))
                    metadata['author'] = safe_convert(pdf_metadata.get('/Author', ''))
                    metadata['subject'] = safe_convert(pdf_metadata.get('/Subject', ''))
                    metadata['creator'] = safe_convert(pdf_metadata.get('/Creator', ''))
                    metadata['producer'] = safe_convert(pdf_metadata.get('/Producer', ''))
                    metadata['creation_date'] = safe_convert(pdf_metadata.get('/CreationDate', ''))
                    metadata['modification_date'] = safe_convert(pdf_metadata.get('/ModDate', ''))
        except Exception as e:
            print(f"Error extracting metadata from {file_path}: {e}")
        
        return metadata
    
    def analyze_single_pdf(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a single PDF file"""
        print(f"Analyzing: {file_path.name}")
        
        # Basic file info
        file_info = {
            'filename': file_path.name,
            'file_path': str(file_path.relative_to(self.data_folder)),
            'folder': str(file_path.parent.relative_to(self.data_folder)),
            'size_mb': self.get_file_size_mb(file_path),
            'extension': file_path.suffix.lower(),
            'last_modified': datetime.fromtimestamp(file_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # PDF-specific analysis
        if file_path.suffix.lower() == '.pdf':
            # Get page count using both methods
            page_count_pypdf2 = self.get_pdf_page_count_pypdf2(file_path)
            page_count_pymupdf = self.get_pdf_page_count_pymupdf(file_path)
            
            # Use the more reliable method
            if page_count_pymupdf is not None:
                file_info['page_count'] = page_count_pymupdf
                file_info['page_count_method'] = 'PyMuPDF'
            elif page_count_pypdf2 is not None:
                file_info['page_count'] = page_count_pypdf2
                file_info['page_count_method'] = 'PyPDF2'
            else:
                file_info['page_count'] = 'Error'
                file_info['page_count_method'] = 'Failed'
            
            # Get metadata
            metadata = self.get_pdf_metadata(file_path)
            file_info.update(metadata)
            
            # Calculate pages per MB
            if isinstance(file_info['page_count'], int) and file_info['size_mb'] > 0:
                file_info['pages_per_mb'] = round(file_info['page_count'] / file_info['size_mb'], 2)
            else:
                file_info['pages_per_mb'] = 'N/A'
        else:
            file_info['page_count'] = 'N/A'
            file_info['page_count_method'] = 'N/A'
            file_info['pages_per_mb'] = 'N/A'
            file_info.update({k: 'N/A' for k in ['title', 'author', 'subject', 'creator', 'producer', 'creation_date', 'modification_date']})
        
        return file_info
    
    def scan_folder_recursively(self) -> List[Dict[str, Any]]:
        """Scan the data folder recursively for PDF files"""
        print(f"Scanning folder: {self.data_folder}")
        
        if not self.data_folder.exists():
            print(f"Error: Folder {self.data_folder} does not exist")
            return []
        
        pdf_files = []
        
        # Find all PDF files recursively
        for file_path in self.data_folder.rglob("*.pdf"):
            if file_path.is_file():
                pdf_files.append(file_path)
        
        print(f"Found {len(pdf_files)} PDF files")
        return pdf_files
    
    def analyze_all_pdfs(self) -> List[Dict[str, Any]]:
        """Analyze all PDF files in the folder"""
        pdf_files = self.scan_folder_recursively()
        
        if not pdf_files:
            print("No PDF files found")
            return []
        
        results = []
        
        for i, file_path in enumerate(pdf_files, 1):
            print(f"Processing {i}/{len(pdf_files)}: {file_path.name}")
            
            try:
                file_info = self.analyze_single_pdf(file_path)
                results.append(file_info)
            except Exception as e:
                print(f"Error analyzing {file_path}: {e}")
                # Add error entry
                results.append({
                    'filename': file_path.name,
                    'file_path': str(file_path.relative_to(self.data_folder)),
                    'folder': str(file_path.parent.relative_to(self.data_folder)),
                    'size_mb': 0.0,
                    'extension': '.pdf',
                    'page_count': 'Error',
                    'page_count_method': 'Failed',
                    'pages_per_mb': 'N/A',
                    'error': str(e)
                })
        
        return results
    
    def generate_excel_report(self, results: List[Dict[str, Any]], output_file: str = "normativa_analysis_report.xlsx"):
        """Generate Excel report with PDF analysis results"""
        if not results:
            print("No results to export")
            return
        
        # Clean data for Excel compatibility
        def clean_for_excel(value):
            if value is None:
                return ""
            if isinstance(value, str):
                # Remove or replace illegal characters
                import re
                # Remove null characters and other problematic chars
                cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', str(value))
                # Replace other problematic characters
                cleaned = cleaned.replace('\x00', '').replace('\x01', '').replace('\x02', '')
                cleaned = cleaned.replace('\x03', '').replace('\x04', '').replace('\x05', '')
                cleaned = cleaned.replace('\x06', '').replace('\x07', '').replace('\x08', '')
                cleaned = cleaned.replace('\x0B', '').replace('\x0C', '').replace('\x0E', '')
                cleaned = cleaned.replace('\x0F', '').replace('\x10', '').replace('\x11', '')
                cleaned = cleaned.replace('\x12', '').replace('\x13', '').replace('\x14', '')
                cleaned = cleaned.replace('\x15', '').replace('\x16', '').replace('\x17', '')
                cleaned = cleaned.replace('\x18', '').replace('\x19', '').replace('\x1A', '')
                cleaned = cleaned.replace('\x1B', '').replace('\x1C', '').replace('\x1D', '')
                cleaned = cleaned.replace('\x1E', '').replace('\x1F', '').replace('\x7F', '')
                return cleaned
            return str(value)
        
        # Clean all string values in results
        cleaned_results = []
        for result in results:
            cleaned_result = {}
            for key, value in result.items():
                cleaned_result[key] = clean_for_excel(value)
            cleaned_results.append(cleaned_result)
        
        # Create DataFrame
        df = pd.DataFrame(cleaned_results)
        
        # Reorder columns for better readability
        column_order = [
            'filename',
            'folder',
            'size_mb',
            'page_count',
            'page_count_method',
            'pages_per_mb',
            'title',
            'author',
            'subject',
            'creator',
            'producer',
            'creation_date',
            'modification_date',
            'last_modified',
            'file_path'
        ]
        
        # Add any missing columns
        for col in column_order:
            if col not in df.columns:
                df[col] = 'N/A'
        
        # Reorder columns
        df = df[column_order]
        
        # Create organized output directory structure
        output_dir = Path("output/analysis")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = output_dir / output_file
        
        # Create Excel writer with multiple sheets
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Main detailed sheet
            df.to_excel(writer, sheet_name='Detailed Analysis', index=False)
            
            # Summary sheet
            self._create_summary_sheet(df, writer)
            
            # Statistics sheet
            self._create_statistics_sheet(df, writer)
        
        print(f"✅ Excel report generated: {output_path}")
        return output_path
    
    def _create_summary_sheet(self, df: pd.DataFrame, writer: pd.ExcelWriter):
        """Create summary sheet"""
        # Filter valid PDFs
        valid_pdfs = df[df['page_count'] != 'Error'].copy()
        
        if valid_pdfs.empty:
            return
        
        # Convert size_mb to numeric
        valid_pdfs['size_mb'] = pd.to_numeric(valid_pdfs['size_mb'], errors='coerce')
        valid_pdfs['page_count'] = pd.to_numeric(valid_pdfs['page_count'], errors='coerce')
        
        # Summary statistics
        summary_data = {
            'Metric': [
                'Total PDF Files',
                'Total Size (MB)',
                'Total Pages',
                'Average File Size (MB)',
                'Average Pages per File',
                'Average Pages per MB',
                'Largest File (MB)',
                'Smallest File (MB)',
                'File with Most Pages',
                'File with Least Pages'
            ],
            'Value': [
                len(valid_pdfs),
                f"{valid_pdfs['size_mb'].sum():.2f}",
                f"{valid_pdfs['page_count'].sum():.0f}",
                f"{valid_pdfs['size_mb'].mean():.2f}",
                f"{valid_pdfs['page_count'].mean():.1f}",
                f"{valid_pdfs['page_count'].sum() / valid_pdfs['size_mb'].sum():.2f}",
                f"{valid_pdfs['size_mb'].max():.2f}",
                f"{valid_pdfs['size_mb'].min():.2f}",
                valid_pdfs.loc[valid_pdfs['page_count'].idxmax(), 'filename'],
                valid_pdfs.loc[valid_pdfs['page_count'].idxmin(), 'filename']
            ]
        }
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
    
    def _create_statistics_sheet(self, df: pd.DataFrame, writer: pd.ExcelWriter):
        """Create statistics sheet with folder analysis"""
        # Filter valid PDFs
        valid_pdfs = df[df['page_count'] != 'Error'].copy()
        
        if valid_pdfs.empty:
            return
        
        # Convert to numeric
        valid_pdfs['size_mb'] = pd.to_numeric(valid_pdfs['size_mb'], errors='coerce')
        valid_pdfs['page_count'] = pd.to_numeric(valid_pdfs['page_count'], errors='coerce')
        
        # Folder statistics
        folder_stats = valid_pdfs.groupby('folder').agg({
            'filename': 'count',
            'size_mb': ['sum', 'mean', 'min', 'max'],
            'page_count': ['sum', 'mean', 'min', 'max']
        }).round(2)
        
        # Flatten column names
        folder_stats.columns = ['_'.join(col).strip() for col in folder_stats.columns]
        folder_stats = folder_stats.reset_index()
        
        # Rename columns for clarity
        folder_stats.columns = [
            'Folder',
            'File Count',
            'Total Size (MB)',
            'Avg Size (MB)',
            'Min Size (MB)',
            'Max Size (MB)',
            'Total Pages',
            'Avg Pages',
            'Min Pages',
            'Max Pages'
        ]
        
        folder_stats.to_excel(writer, sheet_name='Folder Statistics', index=False)
    
    def generate_json_report(self, results: List[Dict[str, Any]], output_file: str = "normativa_analysis_report.json"):
        """Generate JSON report with PDF analysis results"""
        if not results:
            print("No results to export")
            return
        
        # Create organized output directory structure
        output_dir = Path("output/analysis")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = output_dir / output_file
        
        # Add analysis metadata
        report_data = {
            'analysis_date': datetime.now().isoformat(),
            'total_files': len(results),
            'data_folder': str(self.data_folder),
            'results': results
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ JSON report generated: {output_path}")
        return output_path


def main():
    """Main function to run the PDF analysis"""
    print("🔍 PDF Analyzer - Regulatory Documents Analysis")
    print("=" * 50)
    
    # Initialize analyzer
    analyzer = PDFAnalyzer()
    
    # Analyze all PDFs
    print("\n📊 Analyzing PDF files...")
    results = analyzer.analyze_all_pdfs()
    
    if not results:
        print("❌ No PDF files found or analysis failed")
        return
    
    print(f"\n✅ Analysis completed: {len(results)} files processed")
    
    # Generate reports
    print("\n📋 Generating reports...")
    
    # Excel report
    excel_path = analyzer.generate_excel_report(results)
    
    # JSON report
    json_path = analyzer.generate_json_report(results)
    
    # Print summary
    print("\n📈 Analysis Summary:")
    print("-" * 30)
    
    valid_pdfs = [r for r in results if r.get('page_count') != 'Error']
    total_size = sum(r.get('size_mb', 0) for r in valid_pdfs)
    total_pages = sum(r.get('page_count', 0) for r in valid_pdfs if isinstance(r.get('page_count'), int))
    
    print(f"📁 Total PDF files: {len(valid_pdfs)}")
    print(f"💾 Total size: {total_size:.2f} MB")
    print(f"📄 Total pages: {total_pages}")
    print(f"📊 Average pages per file: {total_pages/len(valid_pdfs):.1f}" if valid_pdfs else "N/A")
    print(f"📊 Average pages per MB: {total_pages/total_size:.2f}" if total_size > 0 else "N/A")
    
    print(f"\n📋 Reports generated:")
    print(f"   📊 Excel: {excel_path}")
    print(f"   📄 JSON: {json_path}")


if __name__ == "__main__":
    main() 