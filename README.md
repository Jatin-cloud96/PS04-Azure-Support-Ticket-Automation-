# PS03: Azure Invoice Processing Pipeline

> **Cerevyn Solutions — Round 1 Technical Assessment**  
> **Track**: AI Automation with Azure Implementation  
> **Problem Statement ID**: PS03 (Azure Invoice Processing Pipeline)  
> **Candidate Name**: Jatin Singh  
> **Roll Number**: 2310990616  
> **Branch / Specialization**: Computer Science & Engineering  
> **GitHub Repository**: https://github.com/Jatin-cloud96/PS04-Azure-Support-Ticket-Automation-  
> **Target Cloud**: Microsoft Azure (Functions, Blob Storage, Azurite)

---

## 1. Problem Overview

Document processing in enterprise procurement is plagued by invoice discrepancies, missing vendor fields, arithmetic calculation errors, and duplicate submissions. 

**PS03** requires building an automated, resilient document processing pipeline that:
1. Ingests invoice files from an Azure Blob Storage input container (`invoices-input`).
2. Extracts supplier details, invoice number, date, line items (description, quantity, unit price, total), subtotal, tax amount, and total.
3. Supports both digital PDFs and scanned images via OCR and optical pattern parsing.
4. Audits extraction evidence (page numbers, confidence scores, text snippets) without hallucinating missing values.
5. Validates arithmetic using documented rounding rules (`ROUND_HALF_UP`, 2 decimal places, $\pm 0.01$ tolerance).
6. Separates **`VALID`** invoices into `invoices-output` from records requiring manual intervention (**`REQUIRES_REVIEW`**) into `invoices-review`.
7. Enforces idempotency via SHA-256 fingerprinting to prevent duplicate ingestion.
8. Operates locally with **Azurite** and integrates cleanly with Azure Functions.

---

## 2. Architectural Approach

The system follows **Clean Architecture** principles to decouple business logic from Azure infrastructure bindings:

```
┌──────────────────────────────────────────────────────────┐
│                   Azure Functions App                    │
│             (Trigger & Cloud Infrastructure)             │
│  - Blob Trigger on `invoices-input/{name}`               │
│  - Azure Storage Blob Client Adapter (Azurite / Cloud)   │
└────────────────────────────┬─────────────────────────────┘
                             │ calls
                             ▼
┌──────────────────────────────────────────────────────────┐
│              Decoupled Core Pipeline Service             │
│                (Pure Domain Business Logic)              │
│                                                          │
│  ┌─────────────────┐  ┌──────────────────┐  ┌──────────┐ │
│  │ Deduplication   │  │ Document / OCR   │  │ Rule-set │ │
│  │ SHA-256 Hashes  │  │ Extraction Engine│  │ Validator│ │
│  └─────────────────┘  └──────────────────┘  └──────────┘ │
└────────────────────────────┬─────────────────────────────┘
                             │ routes
                             ▼
┌──────────────────────────────────────────────────────────┐
│                  Azure Blob Storage                      │
│                                                          │
│  ├── invoices-input/       (Raw PDFs / PNGs)             │
│  ├── invoices-output/      (Valid JSON payloads)         │
│  ├── invoices-review/      (Discrepancies & missing)     │
│  ├── invoices-failed/      (Dead-letter / unreadable)    │
│  └── invoices-hashes/      (Idempotency state registry)  │
└──────────────────────────────────────────────────────────┘
```

### Key Architectural Strengths:
- **Zero Hallucination Guarantee**: Missing or uncertain fields are explicitly marked as `None` and tracked in `missing_fields` and `uncertain_fields`.
- **Auditable Evidence Chain**: Every extracted attribute includes confidence scores ($0.0 - 1.0$), source page indices, and verbatim text snippets.
- **Strict Decimal Arithmetic**: Computations use Python's `decimal.Decimal` with `ROUND_HALF_UP` to prevent IEEE-754 floating point inaccuracies.
- **Idempotency & Replay Protection**: Deterministic SHA-256 content hashing blocks duplicate processing and prevents double-posting to accounting ledgers.

---

## 3. Project Directory Structure

```
Cerevyn-Chitkara-RollNumber-PS03/
├── .github/
│   └── workflows/
│       └── ci.yml                     # GitHub Actions automated test & verification workflow
├── docs/
│   └── azure-plan.md                  # Comprehensive Azure Cloud Deployment & IaC Plan
├── sample_data/
│   ├── annotations.json               # Ground-truth annotations for all 5 test scenarios
│   ├── invoices/                      # 5 fictional test invoices
│   │   ├── INV-2026-001_AcmeCorp.pdf                      (Valid digital PDF)
│   │   ├── INV-2026-002_Scanned_ApexLogistics.png         (Valid scanned image)
│   │   ├── INV-2026-003_ArithmeticMismatch_VertexTech.pdf (Arithmetic mismatch)
│   │   ├── INV-2026-004_MissingField_NovaServices.pdf     (Missing invoice number)
│   │   └── INV-2026-005_ZeroTax_BlueOcean.pdf             (Zero tax & penny split)
│   └── expected_outputs/              # Canonical JSON output fixtures
├── scripts/
│   ├── run_local_demo.py              # One-click end-to-end Azurite ingestion & demo runner
│   ├── run_ui.py                      # Interactive Web UI dashboard server (http://localhost:8000)
│   ├── start_azurite.ps1              # Windows Azurite startup script
│   └── start_azurite.sh               # Linux/macOS Azurite startup script
├── src/
│   ├── azure_adapters/
│   │   └── blob_service.py            # Azure Storage Blob adapter (Azurite & Cloud)
│   ├── core/
│   │   ├── models.py                  # Pydantic schemas (LineItem, Evidence, ValidationResult)
│   │   ├── extractor.py               # PDF and OCR optical text extraction engine
│   │   ├── validator.py               # Arithmetic rounding & completeness validator
│   │   ├── deduplication.py           # SHA-256 idempotency & duplicate registry
│   │   └── pipeline.py                # Pipeline service orchestrator
│   ├── evaluation/
│   │   └── evaluate_accuracy.py       # Ground-truth field accuracy benchmark scorer
│   ├── generators/
│   │   └── generate_samples.py        # Programmatic sample generator (PDFs + PNG)
│   └── ui/
│       └── app.py                     # Interactive FastAPI Web Dashboard (SPA with Tailwind)
├── tests/
│   ├── conftest.py                    # Session-scoped test fixtures (Auto-Azurite management)
│   ├── test_extraction.py             # PDF & OCR extraction tests
│   ├── test_validation.py             # Arithmetic, tax, and rounding tests
│   ├── test_missing_fields.py         # Missing field detection tests
│   ├── test_deduplication.py          # SHA-256 idempotency & replay tests
│   ├── test_azure_pipeline.py         # Azure Blob Storage container routing tests
│   └── test_accuracy_benchmark.py     # Automated accuracy regression tests
├── function_app.py                    # Azure Functions v2 Python entrypoint
├── host.json                          # Azure Functions host settings
├── local.settings.json.example        # Credential-free local settings template
├── .env.example                       # Credential-free environment template
├── requirements.txt                   # Production dependency manifest
├── pyproject.toml                     # Python package metadata
└── README.md                          # Main project documentation
```

---

## 4. Dependencies & Prerequisites

### Runtime Requirements
- **Python**: `3.10+` (Tested on `3.11`, `3.12`, and `3.14`)
- **Node.js**: `v18+` or `v20+` (Required to run Azurite emulator)
- **Azurite**: `v3.37.0+` (`npm install -g azurite`)

### Core Python Packages (`requirements.txt`)
- `azure-functions>=2.0.0`
- `azure-storage-blob>=12.20.0`
- `pydantic>=2.7.0`
- `pytest>=8.0.0`
- `pillow>=10.0.0`
- `pypdf>=4.0.0`
- `reportlab>=4.0.0`

---

## 5. Local Setup Instructions

### Step 1: Clone Repository & Create Virtual Environment

```bash
# Clone the repository
git clone https://github.com/<your-username>/Cerevyn-Chitkara-RollNumber-PS03.git
cd Cerevyn-Chitkara-RollNumber-PS03

# Create Python virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate
```

### Step 2: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3: Install & Start Azurite Emulator

```bash
# Install Azurite globally via npm
npm install -g azurite

# Start Azurite (Windows PowerShell)
.\scripts\start_azurite.ps1

# Or start Azurite (Linux / macOS)
bash ./scripts/start_azurite.sh

# Or start directly with CLI
azurite --silent --skipApiVersionCheck --location .azurite --blobHost 127.0.0.1 --blobPort 10000
```

> **Note**: Azurite's default development connection string is:  
> `DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;` (or simply `UseDevelopmentStorage=true`).

---

## 6. How to Run Demonstration, Web UI & Tests

### 6.0 Interactive Web Dashboard (UI)

The project includes an interactive web dashboard providing real-time container visualization, one-click processing, discrepancy inspection, and file uploads:

```bash
# Launch Web Dashboard (auto-opens http://localhost:8000)
.venv\Scripts\python scripts/run_ui.py
```
- **Real-Time Container Overview**: Live counts of `invoices-input`, `invoices-output`, `invoices-review`, `invoices-failed`, and `invoices-hashes`.
- **One-Click Ingestion**: Click *"Run All 5 Samples"* to execute the complete pipeline.
- **Detailed Audit Modal**: Inspect line items, arithmetic verification, confidence evidence, and raw JSON payloads.
- **Accounting & CSV Export**: One-click download of the complete ledger (`/api/export/csv`) or approved-only records (`/api/export/csv?status=VALID`) and full JSON (`/api/export/json`).
- **Custom Uploads**: Drag-and-drop or upload custom invoices.
- **Idempotency Simulator**: Click *"Test Duplicate Replay"* to verify duplicate rejection.

---

### 6.1 One-Click Local Demonstration (CLI)

The automated local demonstration script initializes all containers, ingests the sample invoices, simulates the Azure Function trigger, performs deduplication, audits output containers, and reports accuracy:

```bash
python scripts/run_local_demo.py
```

#### Verbatim Demonstration Output:
```
================================================================================
  PS03 AZURE INVOICE PROCESSING PIPELINE - LOCAL DEMONSTRATION
================================================================================
[Azurite] Starting local Azurite emulator with --skipApiVersionCheck...
[Azurite] Azurite started successfully on port 10000.

[Step 1] Connecting to Azurite and initializing Blob Containers...
 -> Initialized containers: [invoices-input, invoices-output, invoices-review, invoices-failed, invoices-hashes]

[Step 2] Uploading 5 Sample Invoices to 'invoices-input' container...
 -> Uploaded to invoices-input/INV-2026-001_AcmeCorp.pdf (2407 bytes)
 -> Uploaded to invoices-input/INV-2026-002_Scanned_ApexLogistics.png (27744 bytes)
 -> Uploaded to invoices-input/INV-2026-003_ArithmeticMismatch_VertexTech.pdf (2345 bytes)
 -> Uploaded to invoices-input/INV-2026-004_MissingField_NovaServices.pdf (2305 bytes)
 -> Uploaded to invoices-input/INV-2026-005_ZeroTax_BlueOcean.pdf (2346 bytes)

[Step 3] Triggering Processing Pipeline across all ingested invoices...
--------------------------------------------------------------------------------
File Name                                  | Review Status    | Target Container | Latency
--------------------------------------------------------------------------------
INV-2026-001_AcmeCorp.pdf                  | VALID            | invoices-output  | 21.5ms
INV-2026-002_Scanned_ApexLogistics.png     | VALID            | invoices-output  | 45.6ms
INV-2026-003_ArithmeticMismatch_VertexTech.pdf | REQUIRES_REVIEW  | invoices-review  | 11.0ms
   [Discrepancy/Flag] Subtotal mismatch: sum of line items is 700.00, but stated subtotal is 750.00 (difference: 50.00).
INV-2026-004_MissingField_NovaServices.pdf | REQUIRES_REVIEW  | invoices-review  | 12.1ms
   [Discrepancy/Flag] Missing mandatory field(s): invoice_number
INV-2026-005_ZeroTax_BlueOcean.pdf         | VALID            | invoices-output  | 10.3ms

[Step 4] Testing Deduplication / Idempotency Scenario...
 -> Simulating repeated ingestion of: INV-2026-001_AcmeCorp.pdf
 -> Result Status: DUPLICATE_SKIPPED
 -> Audit Message: Duplicate invoice detected with SHA-256: 67bb614d2eea9b3cc7e100a8986232042625801c8577565de98455f62524b2d7. Skipping reprocessing.
 -> SUCCESS: Pipeline prevented duplicate reprocessing and maintained idempotency.

[Step 5] Checking Container Outputs in Azurite...
 -> Invoices Output (VALID):   ['INV-2026-001_AcmeCorp_result.json', 'INV-2026-002_Scanned_ApexLogistics_result.json', 'INV-2026-005_ZeroTax_BlueOcean_result.json']
 -> Invoices Review (FLAGGED): ['INV-2026-003_ArithmeticMismatch_VertexTech_result.json', 'INV-2026-004_MissingField_NovaServices_result.json']

[Step 6] Running Ground-Truth Accuracy Benchmark against annotations.json...
================================================================================
  PS03 INVOICE EXTRACTION & VALIDATION BENCHMARK EVALUATION REPORT
================================================================================
Total Samples Evaluated: 5
Total Field Assertions: 30
Field Accuracy:         100.0% (30/30)
Routing Status Accuracy:100.0%
--------------------------------------------------------------------------------
File Name                                  | Expected         | Actual           | Match
--------------------------------------------------------------------------------
INV-2026-001_AcmeCorp.pdf                  | VALID            | VALID            | [PASS]
INV-2026-002_Scanned_ApexLogistics.png     | VALID            | VALID            | [PASS]
INV-2026-003_ArithmeticMismatch_VertexTech.pdf | REQUIRES_REVIEW  | REQUIRES_REVIEW  | [PASS]
   --> Reason: Subtotal mismatch: sum of line items is 700.00, but stated subtotal is 750.00 (difference: 50.00).
INV-2026-004_MissingField_NovaServices.pdf | REQUIRES_REVIEW  | REQUIRES_REVIEW  | [PASS]
   --> Reason: Missing mandatory field(s): invoice_number
INV-2026-005_ZeroTax_BlueOcean.pdf         | VALID            | VALID            | [PASS]
================================================================================

[SUCCESS] Local demonstration completed successfully!
```

---

### 6.2 Running Automated Pytest Suite

```bash
pytest -v
```

#### Verbatim Test Run Output:
```
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0
cachedir: .pytest_cache
rootdir: C:\Users\...\Cerevyn-Chitkara-RollNumber-PS03
collected 17 items

tests/test_accuracy_benchmark.py::test_full_benchmark_accuracy PASSED    [  5%]
tests/test_azure_pipeline.py::test_azure_blob_routing PASSED             [ 11%]
tests/test_deduplication.py::test_compute_sha256_deterministic PASSED    [ 17%]
tests/test_deduplication.py::test_registry_prevents_duplicate_reprocessing PASSED [ 23%]
tests/test_deduplication.py::test_pipeline_deduplication_e2e PASSED      [ 29%]
tests/test_export.py::test_export_csv_all_records PASSED                 [ 35%]
tests/test_export.py::test_export_csv_filtered_valid_only PASSED         [ 41%]
tests/test_export.py::test_export_json_ledger PASSED                     [ 47%]
tests/test_extraction.py::test_digital_pdf_extraction PASSED             [ 52%]
tests/test_extraction.py::test_scanned_image_ocr_extraction PASSED       [ 58%]
tests/test_extraction.py::test_corrupted_file_handling PASSED            [ 64%]
tests/test_missing_fields.py::test_missing_invoice_number_sample PASSED  [ 70%]
tests/test_missing_fields.py::test_missing_supplier_name PASSED          [ 76%]
tests/test_missing_fields.py::test_empty_line_items PASSED               [ 82%]
tests/test_validation.py::test_arithmetic_mismatch_invoice PASSED        [ 88%]
tests/test_validation.py::test_rounding_half_up_tolerance PASSED         [ 94%]
tests/test_validation.py::test_grand_total_mismatch PASSED               [100%]

============================= 17 passed in 1.12s ==============================
```

---

## 7. Sample Inputs and Expected Outputs

The assessment requires 5 fictional invoices covering at least one scanned image, one arithmetic mismatch, and one missing field:

| Sample Invoice File | Format | Scenario | Expected Status | Resulting Routing |
| :--- | :--- | :--- | :--- | :--- |
| `INV-2026-001_AcmeCorp.pdf` | Digital PDF | Standard multi-line items with 10% tax | `VALID` | `invoices-output/` |
| `INV-2026-002_Scanned_ApexLogistics.png` | Scanned Image (PNG) | Optical scan with receipt border & stamp | `VALID` | `invoices-output/` |
| `INV-2026-003_ArithmeticMismatch_VertexTech.pdf` | Digital PDF | Stated subtotal \$750.00 vs calculated \$700.00 | `REQUIRES_REVIEW` | `invoices-review/` |
| `INV-2026-004_MissingField_NovaServices.pdf` | Digital PDF | Invoice number field omitted/blank | `REQUIRES_REVIEW` | `invoices-review/` |
| `INV-2026-005_ZeroTax_BlueOcean.pdf` | Digital PDF | Zero tax and split-cent items (\$99.99 + \$50.01) | `VALID` | `invoices-output/` |
| *Replayed Input (`INV-2026-001`)* | Binary Replay | Duplicate content SHA-256 | `DUPLICATE_SKIPPED` | Duplicate Logged |

### Sample Output JSON (`INV-2026-001_AcmeCorp_result.json`)
```json
{
  "invoice_id": "INV-2026-001",
  "review_status": "VALID",
  "review_reasons": [],
  "invoice_data": {
    "supplier_name": "Acme Industrial Supplies Ltd",
    "supplier_address": "123 Tech Park, Bengaluru, KA 560100",
    "invoice_number": "INV-2026-001",
    "invoice_date": "2026-03-15",
    "line_items": [
      {
        "description": "Cloud Server Rack Units",
        "quantity": "2",
        "unit_price": "450.00",
        "total_amount": "900.00"
      },
      {
        "description": "Gigabit Ethernet Switch",
        "quantity": "1",
        "unit_price": "120.00",
        "total_amount": "120.00"
      },
      {
        "description": "Cat6 Patch Cables (Pack of 10)",
        "quantity": "4",
        "unit_price": "20.00",
        "total_amount": "80.00"
      }
    ],
    "subtotal": "1100.00",
    "tax_rate_percent": "10",
    "tax_amount": "110.00",
    "total": "1210.00",
    "missing_fields": [],
    "uncertain_fields": [],
    "field_evidence": {
      "invoice_number": {
        "field_name": "invoice_number",
        "value": "INV-2026-001",
        "confidence": 0.98,
        "source_page": 1,
        "text_snippet": "Invoice #: INV-2026-001"
      }
    }
  },
  "arithmetic_validation": {
    "is_valid": true,
    "calculated_subtotal": "1100.00",
    "stated_subtotal": "1100.00",
    "calculated_tax": "110.00",
    "stated_tax": "110.00",
    "calculated_total": "1210.00",
    "stated_total": "1210.00",
    "line_item_math_valid": true,
    "subtotal_tax_sum_valid": true,
    "rounding_method": "ROUND_HALF_UP (2 decimal places, tolerance +/- 0.01)",
    "errors": []
  },
  "metadata": {
    "source_blob_name": "INV-2026-001_AcmeCorp.pdf",
    "file_sha256": "67bb614d2eea9b3cc7e100a8986232042625801c8577565de98455f62524b2d7",
    "file_size_bytes": 2407,
    "content_type": "application/pdf",
    "processed_timestamp_utc": "2026-10-14T17:08:26.543210+00:00",
    "extractor_engine": "PDFTextExtractor",
    "processing_duration_ms": 21.5
  }
}
```

---

## 8. Documented Rounding and Arithmetic Rules

All currency amounts are rounded using `ROUND_HALF_UP` to two decimal places:

1. **Line Item Validation**:
   $$\text{Expected Line Total} = \text{round\_half\_up}(\text{Quantity} \times \text{Unit Price})$$
   $$\text{Discrepancy Flagged if } |\text{Expected} - \text{Stated}| > 0.01$$

2. **Subtotal Validation**:
   $$\text{Calculated Subtotal} = \sum_{i=1}^{n} \text{Stated Line Total}_i$$
   $$\text{Discrepancy Flagged if } |\text{Calculated Subtotal} - \text{Stated Subtotal}| > 0.01$$

3. **Tax Validation**:
   $$\text{Expected Tax} = \text{round\_half\_up}\left(\text{Subtotal} \times \frac{\text{Tax Rate \%}}{100}\right)$$
   $$\text{Discrepancy Flagged if } |\text{Expected Tax} - \text{Stated Tax}| > 0.01$$

4. **Grand Total Validation**:
   $$\text{Calculated Total} = \text{Subtotal} + \text{Tax Amount}$$
   $$\text{Discrepancy Flagged if } |\text{Calculated Total} - \text{Stated Total}| > 0.01$$

---

## 9. Azure Cloud Deployment Plan & Demo Guide

- 📄 **Azure Cloud Architecture & IaC Plan**: [docs/azure-plan.md](docs/azure-plan.md)
- 🎬 **3-to-5 Minute Demo Presentation Script**: [docs/demo-guide.md](docs/demo-guide.md)

---

## 10. Limitations and Future Improvements

1. **Handwritten Invoices**: The local OCR engine excels at printed text, receipt fonts, and digital PDFs. For cursive or handwritten receipts, integration with Azure Document Intelligence (`prebuilt-invoice` model) is recommended in production.
2. **Multi-page Floating Tables**: Line items spanning across multiple pages with repeated headers require layout-aware table boundary detection.
3. **Multi-Currency Normalization**: Current implementation validates domestic currency invoices; multi-currency conversions against real-time FX rates would enhance international procurement.

---

## 11. Author & Maintainer

- **Developer**: Jatin Singh
- **Roll Number**: 2310990616
- **Branch**: Computer Science & Engineering, Chitkara University
- **Repository**: [https://github.com/Jatin-cloud96/PS04-Azure-Support-Ticket-Automation-](https://github.com/Jatin-cloud96/PS04-Azure-Support-Ticket-Automation-)
- **Contact Email**: jatinsinghhh9780@gmail.com
- **Implementation Note**: Complete independent implementation developed according to the Round 1 Technical Assessment brief for Cerevyn Solutions. All architecture, parsing heuristics, arithmetic rounding validations, and Azurite integrations were built and tested locally.
