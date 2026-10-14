# Demonstration Script & Presentation Guide (3 to 5 Minutes)
## PS03: Azure Invoice Processing Pipeline

> **Assessment Track**: AI Automation with Azure Implementation  
> **Problem Statement**: PS03 (Document Automation Pipeline)  
> **Target Audience**: Cerevyn Placement Reviewers & Technical Evaluators

---

## 1. Demonstration Quick Reference

| Demo Time | Section | Screen / Command | Key Talking Point |
| :--- | :--- | :--- | :--- |
| **0:00 - 0:45** | **Architecture & Concept** | Architecture Diagram in README | Decoupled clean architecture, zero-hallucination policy, Azurite cloud parity. |
| **0:45 - 1:45** | **Live Web Dashboard** | Open `http://localhost:8000` | Real-time container state (`invoices-input`, `output`, `review`, `failed`, `hashes`). |
| **1:45 - 3:00** | **The 5 Invoices Walkthrough** | Click "Run All 5 Samples" | Scanned PNG OCR, Arithmetic mismatch detected, Missing field flagged, Zero tax. |
| **3:00 - 3:45** | **Idempotency & Deduplication** | Click "Test Duplicate Replay" | SHA-256 fingerprint blocks duplicate ledger posting. |
| **3:45 - 4:30** | **Automated Tests & Accuracy** | Terminal: `pytest -v` | 14/14 automated tests pass, 100% field accuracy vs `annotations.json`. |
| **4:30 - 5:00** | **Azure Cloud Deployment Plan** | `docs/azure-plan.md` | Managed Identity, Key Vault, Application Insights, Consumption scaling. |

---

## 2. Step-by-Step Spoken Walkthrough Script

### [0:00 - 0:45] Introduction & Problem Context
> *"Hello! Today I am presenting my solution for Problem Statement PS03: the Azure Invoice Processing Pipeline.*  
> *In accounts payable, receiving invoices with calculation errors, missing vendor details, or duplicate submissions causes costly billing errors and manual overhead.*  
> *To solve this, I designed a serverless document automation pipeline that extracts invoice data from digital PDFs and scanned images, checks arithmetic using strict financial rounding rules, enforces idempotency to prevent duplicate processing, and automatically separates valid invoices from records requiring review — demonstrated entirely on local Azure Blob Storage using Azurite."*

### [0:45 - 1:45] The Web Dashboard & Storage Containers
> *"Here on the screen is the interactive Web Dashboard running locally on FastAPI and connected to Azurite on port 10000.*  
> *At the top, we see the 5 partitioned Azure Blob containers:*  
> *1. `invoices-input` for raw incoming invoices.*  
> *2. `invoices-output` for verified records with status VALID.*  
> *3. `invoices-review` for flagged invoices requiring human intervention.*  
> *4. `invoices-failed` as a dead-letter queue for unreadable payloads.*  
> *5. `invoices-hashes` which stores SHA-256 fingerprint records to guarantee idempotency."*

### [1:45 - 3:00] Processing the 5 Mandated Scenarios
> *"Now, I will click 'Run All 5 Samples'. Notice how quickly the pipeline executes across all 5 test scenarios:*  
> *1. First, `INV-2026-001` is a digital PDF with 3 line items and 10% tax. All arithmetic matches perfectly, so it is marked VALID and routed to `invoices-output`.*  
> *2. Second, `INV-2026-002` is a high-resolution scanned PNG image with receipt borders, paper texture, and a stamp. The optical extraction engine reads all fields accurately without inventing data, and it is marked VALID.*  
> *3. Third, `INV-2026-003` tests the Arithmetic Mismatch requirement. The line items sum to \$700, but the vendor wrote \$750 on the subtotal. The validator immediately catches the \$50 mismatch and routes it to `invoices-review` with the exact explanation.*  
> *4. Fourth, `INV-2026-004` tests the Missing Field requirement. The invoice number was omitted. Under our zero-hallucination policy, we never invent fake data; the pipeline marks the field as None and routes it to `invoices-review`.*  
> *5. Fifth, `INV-2026-005` demonstrates zero-rated tax and fractional penny splits (\$99.99 + \$50.01 = \$150.00), verifying our ROUND_HALF_UP two-decimal rounding rules."*

### [3:00 - 3:45] Idempotency & Deduplication
> *"Next, I click 'Test Duplicate Replay'. A vendor accidentally re-uploads `INV-2026-001`. Instead of re-extracting or creating a duplicate payment entry, the pipeline checks the SHA-256 hash registry, marks it `DUPLICATE_SKIPPED`, and stops processing. This guarantees idempotency."*

### [3:45 - 4:30] Accuracy Benchmarking & Automated Tests
> *"In the terminal, running `pytest -v` executes 14 comprehensive automated unit, integration, and failure-handling tests in under 1 second.*  
> *Furthermore, our accuracy benchmark script compares every single extracted field against the ground-truth `annotations.json` file, achieving 100.0% field extraction accuracy and 100.0% routing accuracy."*

### [4:30 - 5:00] Azure Cloud Production Readiness
> *"Finally, in `docs/azure-plan.md`, I have documented the complete cloud architecture:*  
> *• Azure Functions on Linux Consumption Plan for scale-to-zero economics.*  
> *• System-Assigned Managed Identity and Key Vault for zero hardcoded secrets.*  
> *• Application Insights for custom metric telemetry.*  
> *• Storage lifecycle policies saving up to 85% on long-term retention costs.*  
> *Thank you for your time!"*

---

## 3. Visual UI Representation (Dashboard Layout)

```
┌────────────────────────────────────────────────────────────────────────────┐
│ [Icon] Invoice Processing Pipeline [PS03]   [● Azurite Connected: 10000]   │
├────────────────────────────────────────────────────────────────────────────┤
│ [ VALID: 3 ]      [ REQUIRES_REVIEW: 2 ]    [ ACCURACY: 100% ]   [ DEDUP ] │
├────────────────────────────────────────────────────────────────────────────┤
│ Azure Containers: [invoices-input] [invoices-output] [invoices-review]     │
│                   [invoices-failed] [invoices-hashes]                      │
│                                                                            │
│ Actions: [▷ Run All 5 Samples]  [⎘ Test Duplicate Replay]  [↑ Upload File] │
├────────────────────────────────────────────────────────────────────────────┤
│ Document               | Status   | Supplier            | Total    | Detail│
├────────────────────────────────────────────────────────────────────────────┤
│ INV-001_AcmeCorp.pdf   | VALID    | Acme Supplies Ltd   | $1210.00 | [View]│
│ INV-002_Scanned.png    | VALID    | Apex Logistics Corp | $1062.00 | [View]│
│ INV-003_Mismatch.pdf   | REVIEW   | Vertex Cloud Inc    | $825.00  | [View]│
│   ↳ Subtotal mismatch: line items sum is $700.00, stated is $750.00        │
│ INV-004_Missing.pdf    | REVIEW   | Nova Consulting LLP | $1416.00 | [View]│
│   ↳ Missing mandatory field(s): invoice_number                             │
│ INV-005_ZeroTax.pdf    | VALID    | Blue Ocean Softwares| $150.00  | [View]│
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Verification Checkpoints

- [x] Azurite storage emulator running on port 10000 (`azurite --skipApiVersionCheck`)
- [x] Web dashboard accessible at `http://localhost:8000` (`python scripts/run_ui.py`)
- [x] CLI demonstration runner executes cleanly (`python scripts/run_local_demo.py`)
- [x] Pytest suite passes 14/14 tests (`pytest -v`)
- [x] Field accuracy against `sample_data/annotations.json` is 100.0%
- [x] Expected outputs and failure/retry logs documented in `sample_data/expected_outputs/`
