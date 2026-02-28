#!/usr/bin/env python3
"""
AirAd Vendor Portal User Manual - PDF Export Script
Converts the HTML manual to a professionally formatted PDF
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def create_pdf_manual():
    """Create PDF version of the AirAd Vendor Portal User Manual"""
    
    # Check if we can use weasyprint for PDF generation
    try:
        from weasyprint import HTML, CSS
        print("✓ WeasyPrint available - creating professional PDF...")
        
        # Paths
        html_path = project_root / "docs" / "AirAd_Vendor_Portal_User_Manual.html"
        pdf_path = project_root / "docs" / "AirAd_Vendor_Portal_User_Manual.pdf"
        
        # Read the HTML content
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Custom CSS for print optimization
        print_css = CSS(string="""
            @page {
                size: A4;
                margin: 2cm;
                @bottom-center {
                    content: counter(page);
                    font-size: 10px;
                    color: #666;
                }
                @top-center {
                    content: "AirAd Vendor Portal - User Manual";
                    font-size: 10px;
                    color: #666;
                }
            }
            
            body {
                font-size: 12px;
                line-height: 1.4;
            }
            
            .page {
                width: 100%;
                height: auto;
                margin: 0;
                padding: 0;
                box-shadow: none;
                page-break-after: always;
            }
            
            .page-break {
                page-break-before: always;
            }
            
            .header {
                text-align: center;
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 2px solid #FF6B35;
            }
            
            .logo {
                width: 60px;
                height: 60px;
            }
            
            .title {
                font-size: 24px;
                margin-bottom: 5px;
            }
            
            .section-title {
                font-size: 18px;
                margin-bottom: 15px;
            }
            
            .subsection-title {
                font-size: 14px;
                margin-bottom: 10px;
            }
            
            .text-content {
                font-size: 11px;
                margin-bottom: 15px;
            }
            
            .tier-table {
                font-size: 9px;
            }
            
            .feature-card {
                margin-bottom: 10px;
                padding: 10px;
            }
            
            .tip-box, .warning-box {
                margin: 10px 0;
                padding: 8px;
            }
            
            .step-list li {
                font-size: 10px;
                margin-bottom: 8px;
            }
            
            .faq-item {
                margin-bottom: 15px;
                padding: 10px;
            }
            
            .footer {
                position: static;
                text-align: center;
                margin-top: 20px;
                padding-top: 10px;
                border-top: 1px solid #ccc;
                font-size: 9px;
            }
        """)
        
        # Generate PDF
        html_doc = HTML(string=html_content, base_url=str(html_path.parent))
        html_doc.write_pdf(str(pdf_path), stylesheets=[print_css])
        
        print(f"✓ PDF created successfully: {pdf_path}")
        print(f"  File size: {os.path.getsize(pdf_path):,} bytes")
        
        return True
        
    except ImportError:
        print("⚠ WeasyPrint not available - creating alternative PDF...")
        return create_alternative_pdf()

def create_alternative_pdf():
    """Alternative PDF creation method using basic HTML to PDF conversion"""
    
    try:
        import subprocess
        
        # Paths
        html_path = project_root / "docs" / "AirAd_Vendor_Portal_User_Manual.html"
        pdf_path = project_root / "docs" / "AirAd_Vendor_Portal_User_Manual.pdf"
        
        # Try using wkhtmltopdf if available
        try:
            result = subprocess.run([
                'wkhtmltopdf',
                '--page-size', 'A4',
                '--margin-top', '2cm',
                '--margin-bottom', '2cm',
                '--margin-left', '2cm',
                '--margin-right', '2cm',
                '--footer-center', '[page]',
                '--header-center', 'AirAd Vendor Portal - User Manual',
                '--header-font-size', '10',
                '--footer-font-size', '10',
                str(html_path),
                str(pdf_path)
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✓ PDF created with wkhtmltopdf: {pdf_path}")
                return True
            else:
                print(f"❌ wkhtmltopdf error: {result.stderr}")
                
        except FileNotFoundError:
            print("⚠ wkhtmltopdf not available")
        
        # Create a simple text-based manual as fallback
        return create_text_manual()
        
    except Exception as e:
        print(f"❌ PDF creation failed: {e}")
        return create_text_manual()

def create_text_manual():
    """Create a text-based manual as fallback"""
    
    print("📝 Creating text-based manual...")
    
    # Paths
    html_path = project_root / "docs" / "AirAd_Vendor_Portal_User_Manual.html"
    txt_path = project_root / "docs" / "AirAd_Vendor_Portal_User_Manual.txt"
    
    try:
        # Basic HTML to text conversion
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Simple text extraction (basic)
        import re
        
        # Remove HTML tags
        text_content = re.sub(r'<[^>]+>', '\n', html_content)
        
        # Clean up whitespace
        text_content = re.sub(r'\n\s*\n', '\n\n', text_content)
        text_content = text_content.strip()
        
        # Add header
        header = """
AIRAD VENDOR PORTAL - USER MANUAL
=====================================
Version 1.0 | February 2026

"""
        
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(header + text_content)
        
        print(f"✓ Text manual created: {txt_path}")
        print("📋 For PDF generation, install WeasyPrint: pip install weasyprint")
        
        return True
        
    except Exception as e:
        print(f"❌ Text manual creation failed: {e}")
        return False

def main():
    """Main execution function"""
    print("🚀 Creating AirAd Vendor Portal User Manual...")
    print("=" * 50)
    
    # Verify HTML manual exists
    html_path = project_root / "docs" / "AirAd_Vendor_Portal_User_Manual.html"
    if not html_path.exists():
        print(f"❌ HTML manual not found: {html_path}")
        return False
    
    print(f"✓ HTML manual found: {html_path}")
    print(f"  File size: {os.path.getsize(html_path):,} bytes")
    
    # Create PDF
    success = create_pdf_manual()
    
    if success:
        print("\n🎉 Manual creation completed successfully!")
        print("\n📁 Available files:")
        
        docs_dir = project_root / "docs"
        for file in docs_dir.glob("AirAd_Vendor_Portal_User_Manual.*"):
            size = os.path.getsize(file)
            print(f"  📄 {file.name} ({size:,} bytes)")
        
        print(f"\n📂 Manual location: {docs_dir}")
        print("\n✅ Ready for distribution to vendors!")
        
    else:
        print("\n❌ Manual creation failed")
        print("📋 Please check the error messages above")
    
    return success

if __name__ == "__main__":
    main()
