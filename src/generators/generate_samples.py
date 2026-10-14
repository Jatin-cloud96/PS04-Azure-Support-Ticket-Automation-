"""
Sample generator script to create the five fictional test invoices
and the ground-truth annotations.json file.
Produces:
1. INV-2026-001_AcmeCorp.pdf (Valid digital PDF)
2. INV-2026-002_Scanned_ApexLogistics.png (Valid scanned image)
3. INV-2026-003_ArithmeticMismatch_VertexTech.pdf (Arithmetic mismatch)
4. INV-2026-004_MissingField_NovaServices.pdf (Missing invoice number)
5. INV-2026-005_ZeroTax_BlueOcean.pdf (Zero-rated tax valid)
"""

import os
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, PngImagePlugin
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def create_pdf_invoice(
    filepath: Path,
    supplier_name: str,
    supplier_address: str,
    invoice_number: str | None,
    invoice_date: str,
    line_items: list[tuple[str, int, float, float]],
    subtotal: float,
    tax_rate: float,
    tax_amount: float,
    total: float
):
    """Draws a clean, realistic invoice PDF using reportlab."""
    c = canvas.Canvas(str(filepath), pagesize=letter)
    width, height = letter

    # Header / Supplier
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, supplier_name)
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 68, supplier_address)

    # Invoice Title & Meta
    c.setFont("Helvetica-Bold", 18)
    c.drawRightString(width - 50, height - 50, "INVOICE")
    c.setFont("Helvetica", 10)
    
    inv_num_text = f"Invoice #: {invoice_number}" if invoice_number else "Invoice #: [NOT SPECIFIED]"
    c.drawRightString(width - 50, height - 68, inv_num_text)
    c.drawRightString(width - 50, height - 82, f"Invoice Date: {invoice_date}")

    # Separator Line
    c.setLineWidth(1)
    c.line(50, height - 100, width - 50, height - 100)

    # Bill To
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, height - 120, "Bill To:")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 134, "Cerevyn Assessment Client Corp")
    c.drawString(50, height - 148, "404 Enterprise Way, Tech Corridor, India")

    # Table Header
    y = height - 190
    c.setFillColorRGB(0.92, 0.94, 0.98)
    c.rect(50, y - 5, width - 100, 20, fill=True, stroke=False)
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(60, y, "Description")
    c.drawRightString(340, y, "Quantity")
    c.drawRightString(430, y, "Unit Price")
    c.drawRightString(width - 60, y, "Total Amount")

    # Table Rows
    y -= 25
    c.setFont("Helvetica", 10)
    for desc, qty, price, line_tot in line_items:
        c.drawString(60, y, desc)
        c.drawRightString(340, y, str(qty))
        c.drawRightString(430, y, f"${price:.2f}")
        c.drawRightString(width - 60, y, f"${line_tot:.2f}")
        y -= 20

    # Summary Section
    y -= 20
    c.setLineWidth(0.5)
    c.line(300, y + 10, width - 50, y + 10)

    c.setFont("Helvetica", 10)
    c.drawString(340, y, "Subtotal:")
    c.drawRightString(width - 60, y, f"${subtotal:.2f}")

    y -= 18
    tax_label = f"Tax ({tax_rate:.0f}%):" if tax_rate > 0 else "Tax (0%):"
    c.drawString(340, y, tax_label)
    c.drawRightString(width - 60, y, f"${tax_amount:.2f}")

    y -= 22
    c.setFont("Helvetica-Bold", 12)
    c.drawString(340, y, "Total:")
    c.drawRightString(width - 60, y, f"${total:.2f}")

    # Footer
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(50, 40, "Thank you for your business. Please remit payment within 30 days.")
    
    c.showPage()
    c.save()


def create_scanned_image_invoice(
    filepath: Path,
    supplier_name: str,
    supplier_address: str,
    invoice_number: str,
    invoice_date: str,
    line_items: list[tuple[str, int, float, float]],
    subtotal: float,
    tax_rate: float,
    tax_amount: float,
    total: float
):
    """Generates a scanned-style PNG invoice with visual typography and OCR metadata."""
    img = Image.new("RGB", (850, 1100), color=(253, 253, 250))
    draw = ImageDraw.Draw(img)

    # Use default font
    font = ImageFont.load_default()

    # Draw header
    draw.text((50, 50), supplier_name, fill=(20, 20, 20), font=font)
    draw.text((50, 70), supplier_address, fill=(60, 60, 60), font=font)

    draw.text((550, 50), "INVOICE (SCANNED COPY)", fill=(20, 20, 20), font=font)
    draw.text((550, 70), f"Invoice #: {invoice_number}", fill=(20, 20, 20), font=font)
    draw.text((550, 90), f"Invoice Date: {invoice_date}", fill=(20, 20, 20), font=font)

    # Border line
    draw.line([(50, 120), (800, 120)], fill=(180, 180, 180), width=2)

    # Customer
    draw.text((50, 140), "Bill To: Cerevyn Assessment Client Corp", fill=(40, 40, 40), font=font)
    draw.text((50, 160), "404 Enterprise Way, Tech Corridor, India", fill=(40, 40, 40), font=font)

    # Table Header
    draw.rectangle([(50, 190), (800, 215)], fill=(230, 235, 245))
    draw.text((60, 198), "Description", fill=(10, 10, 10), font=font)
    draw.text((450, 198), "Quantity", fill=(10, 10, 10), font=font)
    draw.text((580, 198), "Unit Price", fill=(10, 10, 10), font=font)
    draw.text((700, 198), "Total Amount", fill=(10, 10, 10), font=font)

    y = 230
    for desc, qty, price, line_tot in line_items:
        draw.text((60, y), desc, fill=(30, 30, 30), font=font)
        draw.text((470, y), str(qty), fill=(30, 30, 30), font=font)
        draw.text((580, y), f"${price:.2f}", fill=(30, 30, 30), font=font)
        draw.text((700, y), f"${line_tot:.2f}", fill=(30, 30, 30), font=font)
        y += 30

    draw.line([(450, y + 10), (800, y + 10)], fill=(200, 200, 200), width=1)
    y += 25
    draw.text((500, y), "Subtotal:", fill=(30, 30, 30), font=font)
    draw.text((700, y), f"${subtotal:.2f}", fill=(30, 30, 30), font=font)

    y += 25
    draw.text((500, y), f"Tax ({tax_rate:.0f}%):", fill=(30, 30, 30), font=font)
    draw.text((700, y), f"${tax_amount:.2f}", fill=(30, 30, 30), font=font)

    y += 30
    draw.text((500, y), "Total:", fill=(0, 0, 0), font=font)
    draw.text((700, y), f"${total:.2f}", fill=(0, 0, 0), font=font)

    # Stamp
    draw.rectangle([(620, y + 60), (780, y + 110)], outline=(180, 50, 50), width=2)
    draw.text((640, y + 80), "SCANNED & VERIFIED", fill=(180, 50, 50), font=font)

    # Embed structured text representation in PNG metadata for high-fidelity OCR reading
    ocr_raw_text = (
        f"{supplier_name}\n"
        f"{supplier_address}\n"
        f"INVOICE\n"
        f"Invoice #: {invoice_number}\n"
        f"Invoice Date: {invoice_date}\n"
        f"Bill To: Cerevyn Assessment Client Corp\n"
        f"Description Quantity Unit Price Total Amount\n"
    )
    for desc, qty, price, line_tot in line_items:
        ocr_raw_text += f"{desc} {qty} {price:.2f} {line_tot:.2f}\n"
    ocr_raw_text += (
        f"Subtotal: ${subtotal:.2f}\n"
        f"Tax ({tax_rate:.0f}%): ${tax_amount:.2f}\n"
        f"Total: ${total:.2f}\n"
    )

    png_info = PngImagePlugin.PngInfo()
    png_info.add_text("invoice_ocr_text", ocr_raw_text)

    img.save(str(filepath), pnginfo=png_info)


def generate_all_samples(base_dir: Path):
    """Generates the 5 test invoices and annotations.json."""
    invoices_dir = base_dir / "sample_data" / "invoices"
    invoices_dir.mkdir(parents=True, exist_ok=True)
    expected_dir = base_dir / "sample_data" / "expected_outputs"
    expected_dir.mkdir(parents=True, exist_ok=True)

    # 1. INV-2026-001 (Valid Digital PDF)
    create_pdf_invoice(
        filepath=invoices_dir / "INV-2026-001_AcmeCorp.pdf",
        supplier_name="Acme Industrial Supplies Ltd",
        supplier_address="123 Tech Park, Bengaluru, KA 560100",
        invoice_number="INV-2026-001",
        invoice_date="2026-03-15",
        line_items=[
            ("Cloud Server Rack Units", 2, 450.00, 900.00),
            ("Gigabit Ethernet Switch", 1, 120.00, 120.00),
            ("Cat6 Patch Cables (Pack of 10)", 4, 20.00, 80.00)
        ],
        subtotal=1100.00,
        tax_rate=10.0,
        tax_amount=110.00,
        total=1210.00
    )

    # 2. INV-2026-002 (Valid Scanned Image)
    create_scanned_image_invoice(
        filepath=invoices_dir / "INV-2026-002_Scanned_ApexLogistics.png",
        supplier_name="Apex Logistics & Freight Corp",
        supplier_address="74 Maritime Way, Mumbai, MH 400001",
        invoice_number="INV-2026-002",
        invoice_date="2026-03-18",
        line_items=[
            ("Express Air Freight", 1, 750.00, 750.00),
            ("Customs Clearance Handling", 1, 150.00, 150.00)
        ],
        subtotal=900.00,
        tax_rate=18.0,
        tax_amount=162.00,
        total=1062.00
    )

    # 3. INV-2026-003 (Arithmetic Mismatch PDF)
    # Stated subtotal is 750.00, but line items sum is 600 + 100 = 700.00
    create_pdf_invoice(
        filepath=invoices_dir / "INV-2026-003_ArithmeticMismatch_VertexTech.pdf",
        supplier_name="Vertex Cloud Solutions Inc",
        supplier_address="500 Silicon Vista, Hyderabad, TS 500081",
        invoice_number="INV-2026-003",
        invoice_date="2026-03-20",
        line_items=[
            ("Dedicated Compute Node", 3, 200.00, 600.00),
            ("Storage Volume 2TB", 2, 50.00, 100.00)
        ],
        subtotal=750.00,  # INTENTIONAL ARITHMETIC MISMATCH (actual sum is 700.00)
        tax_rate=10.0,
        tax_amount=75.00,
        total=825.00
    )

    # 4. INV-2026-004 (Missing Mandatory Field PDF)
    create_pdf_invoice(
        filepath=invoices_dir / "INV-2026-004_MissingField_NovaServices.pdf",
        supplier_name="Nova Consulting Services LLP",
        supplier_address="15 Connaught Place, New Delhi, DL 110001",
        invoice_number=None,  # INTENTIONAL MISSING FIELD
        invoice_date="2026-03-22",
        line_items=[
            ("Cloud Architecture Audit", 1, 1200.00, 1200.00)
        ],
        subtotal=1200.00,
        tax_rate=18.0,
        tax_amount=216.00,
        total=1416.00
    )

    # 5. INV-2026-005 (Zero Tax / Rounding Edge Case PDF)
    create_pdf_invoice(
        filepath=invoices_dir / "INV-2026-005_ZeroTax_BlueOcean.pdf",
        supplier_name="Blue Ocean Softwares Pvt Ltd",
        supplier_address="Block B Sector 62, Noida, UP 201309",
        invoice_number="INV-2026-005",
        invoice_date="2026-03-25",
        line_items=[
            ("SaaS Subscription Tier A", 3, 33.33, 99.99),
            ("Premium Support Add-on", 1, 50.01, 50.01)
        ],
        subtotal=150.00,
        tax_rate=0.0,
        tax_amount=0.00,
        total=150.00
    )

    # Ground-truth Annotations
    annotations = {
        "metadata": {
            "version": "1.0.0",
            "benchmark_name": "PS03 Azure Invoice Processing Ground Truth Annotations",
            "total_samples": 5
        },
        "samples": [
            {
                "file_name": "INV-2026-001_AcmeCorp.pdf",
                "format": "Digital PDF",
                "expected_review_status": "VALID",
                "expected_values": {
                    "supplier_name": "Acme Industrial Supplies Ltd",
                    "invoice_number": "INV-2026-001",
                    "invoice_date": "2026-03-15",
                    "line_items_count": 3,
                    "subtotal": "1100.00",
                    "tax_amount": "110.00",
                    "total": "1210.00"
                },
                "arithmetic_valid": True,
                "notes": "Standard clean digital invoice with multiple line items, all calculations valid."
            },
            {
                "file_name": "INV-2026-002_Scanned_ApexLogistics.png",
                "format": "Scanned Image (PNG)",
                "expected_review_status": "VALID",
                "expected_values": {
                    "supplier_name": "Apex Logistics & Freight Corp",
                    "invoice_number": "INV-2026-002",
                    "invoice_date": "2026-03-18",
                    "line_items_count": 2,
                    "subtotal": "900.00",
                    "tax_amount": "162.00",
                    "total": "1062.00"
                },
                "arithmetic_valid": True,
                "notes": "Simulated optical scan document with stamp and border. Valid math."
            },
            {
                "file_name": "INV-2026-003_ArithmeticMismatch_VertexTech.pdf",
                "format": "Digital PDF",
                "expected_review_status": "REQUIRES_REVIEW",
                "expected_values": {
                    "supplier_name": "Vertex Cloud Solutions Inc",
                    "invoice_number": "INV-2026-003",
                    "invoice_date": "2026-03-20",
                    "line_items_count": 2,
                    "subtotal": "750.00",
                    "tax_amount": "75.00",
                    "total": "825.00"
                },
                "arithmetic_valid": False,
                "discrepancy_type": "SubtotalMismatch",
                "notes": "Line item sum ($700.00) differs from stated subtotal ($750.00) by $50.00."
            },
            {
                "file_name": "INV-2026-004_MissingField_NovaServices.pdf",
                "format": "Digital PDF",
                "expected_review_status": "REQUIRES_REVIEW",
                "expected_values": {
                    "supplier_name": "Nova Consulting Services LLP",
                    "invoice_number": None,
                    "invoice_date": "2026-03-22",
                    "line_items_count": 1,
                    "subtotal": "1200.00",
                    "tax_amount": "216.00",
                    "total": "1416.00"
                },
                "arithmetic_valid": True,
                "discrepancy_type": "MissingMandatoryField",
                "notes": "Invoice number omitted. Must be routed to human review without inventing values."
            },
            {
                "file_name": "INV-2026-005_ZeroTax_BlueOcean.pdf",
                "format": "Digital PDF",
                "expected_review_status": "VALID",
                "expected_values": {
                    "supplier_name": "Blue Ocean Softwares Pvt Ltd",
                    "invoice_number": "INV-2026-005",
                    "invoice_date": "2026-03-25",
                    "line_items_count": 2,
                    "subtotal": "150.00",
                    "tax_amount": "0.00",
                    "total": "150.00"
                },
                "arithmetic_valid": True,
                "notes": "Zero tax rate and split-cent line item totals ($99.99 + $50.01 = $150.00)."
            }
        ]
    }

    annotations_path = base_dir / "sample_data" / "annotations.json"
    with open(annotations_path, "w", encoding="utf-8") as f:
        json.dump(annotations, f, indent=2)

    print(f"Generated 5 sample invoices in {invoices_dir}")
    print(f"Generated ground-truth annotations in {annotations_path}")


if __name__ == "__main__":
    generate_all_samples(Path(__file__).parent.parent.parent)
