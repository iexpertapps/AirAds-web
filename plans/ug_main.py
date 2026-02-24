"""
AirAd Data Collection Portal — User Guide Main Runner
Run this script to produce the final .docx file.

Usage:
    cd /Users/syedsmacbook/Developer/AirAds-web/plans
    pip install python-docx
    python3 ug_main.py

Output:
    AirAd_Data_Collection_Portal_User_Guide.docx
"""

import sys
import os

# Ensure the plans directory is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH

import ug_sec1_4
import ug_sec5_9
import ug_sec10_18


def setup_document():
    doc = Document()

    # Page margins
    for section in doc.sections:
        section.top_margin    = Cm(2.0)
        section.bottom_margin = Cm(2.0)
        section.left_margin   = Cm(2.5)
        section.right_margin  = Cm(2.5)

    # Default paragraph font
    style = doc.styles['Normal']
    style.font.name = 'Calibri'
    style.font.size = Pt(10.5)

    # Heading styles
    for lvl, sz, bold in [('Heading 1', 14, True), ('Heading 2', 12, True)]:
        s = doc.styles[lvl]
        s.font.name = 'Calibri'
        s.font.size = Pt(sz)
        s.font.bold = bold

    return doc


def main():
    print("Building AirAd Data Collection Portal User Guide...")

    doc = setup_document()

    print("  Writing Sections 1-4 (Introduction, Roles, Login, Dashboard)...")
    ug_sec1_4.build(doc)

    print("  Writing Sections 5-9 (Geo, Vendors, CSV Import, Field Ops, QA)...")
    ug_sec5_9.build(doc)

    print("  Writing Sections 10-18 (Tags, Governance, Audit, Users, Statuses, FAQ, Glossary, Privacy)...")
    ug_sec10_18.build(doc)

    output_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "AirAd_Data_Collection_Portal_User_Guide.docx"
    )
    doc.save(output_path)
    print(f"\nDone! User Guide saved to:\n  {output_path}")


if __name__ == "__main__":
    main()
