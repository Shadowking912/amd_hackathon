#!/usr/bin/env python3
"""
CaptionChameleon - Presentation PDF Generator
Converts presentation HTML to PDF using weasyprint
"""

import subprocess
import sys
from pathlib import Path

def generate_presentation_pdf(html_path, pdf_path):
    """Convert HTML presentation to PDF"""
    print(f"Converting presentation HTML to PDF...")
    print(f"  Input:  {html_path}")
    print(f"  Output: {pdf_path}")
    
    try:
        # Use weasyprint to convert HTML to PDF
        from weasyprint import HTML, CSS
        
        HTML(string=Path(html_path).read_text()).write_pdf(pdf_path)
        
        file_size_kb = Path(pdf_path).stat().st_size / 1024
        print(f"\n✓ PDF generated successfully!")
        print(f"  File: {pdf_path}")
        print(f"  Size: {file_size_kb:.1f} KB")
        return True
        
    except ImportError:
        print("⚠ weasyprint not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "weasyprint"], check=True)
        
        from weasyprint import HTML, CSS
        HTML(string=Path(html_path).read_text()).write_pdf(pdf_path)
        
        file_size_kb = Path(pdf_path).stat().st_size / 1024
        print(f"\n✓ PDF generated successfully!")
        print(f"  File: {pdf_path}")
        print(f"  Size: {file_size_kb:.1f} KB")
        return True
    except Exception as e:
        print(f"✗ Error generating PDF: {e}")
        return False

if __name__ == "__main__":
    script_dir = Path(__file__).parent
    html_file = script_dir / "presentation_template.html"
    pdf_file = script_dir.parent / "submission" / "CaptionChameleon_Presentation.pdf"
    
    if not html_file.exists():
        print(f"Error: {html_file} not found")
        sys.exit(1)
    
    generate_presentation_pdf(str(html_file), str(pdf_file))
