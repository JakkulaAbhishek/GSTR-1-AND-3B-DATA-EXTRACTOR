"""
================================================================================
GST Report Generator - Fully Automated Version
================================================================================
Author   : Jakkula Abhishek
Email    : Jakkulaabhishek5@gmail.com
Version  : 3.0 (Ultimate)
Features :
    - Upload any GSTR-1 and GSTR-3B PDFs (any filenames)
    - Auto-detect tax period from PDF content
    - Extract all critical tables using pdfplumber
    - Generate Excel reports (multi-month GSTR-3B and combined GSTR-1)
    - Interactive dashboard with KPIs, monthly trends, and charts
    - Data validation, error logging, caching for performance
    - Beautiful modern UI with branding and responsive layout
================================================================================
"""

import streamlit as st
import pandas as pd
import pdfplumber
import re
import io
import base64
import json
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Any
import warnings
warnings.filterwarnings('ignore')

# =============================================================================
# PAGE CONFIGURATION & BRANDING
# =============================================================================
st.set_page_config(
    page_title="GST Report Generator - Jakkula Abhishek",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for premium look
st.markdown("""
<style>
    /* Main background */
    .stApp {
        background: linear-gradient(135deg, #f0f2f6 0%, #e9ecef 100%);
    }
    /* Header card */
    .header-card {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        border-radius: 25px;
        padding: 1.8rem;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        color: white;
    }
    .brand-name {
        font-size: 2.8rem;
        font-weight: 800;
        letter-spacing: 1px;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .brand-email {
        font-size: 1.2rem;
        margin-top: 0.5rem;
        opacity: 0.9;
    }
    .subtitle {
        font-size: 1.1rem;
        margin-top: 1rem;
        font-weight: 400;
    }
    /* Cards for upload sections */
    .upload-card {
        background: white;
        border-radius: 20px;
        padding: 1.5rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 1.5rem;
        transition: transform 0.2s;
    }
    .upload-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.1);
    }
    /* Custom button */
    .stButton > button {
        background: linear-gradient(90deg, #1e3c72, #2a5298);
        color: white;
        border-radius: 40px;
        padding: 0.6rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        border: none;
        transition: 0.3s;
    }
    .stButton > button:hover {
        background: linear-gradient(90deg, #2a5298, #1e3c72);
        transform: scale(1.02);
        color: white;
    }
    /* Success message */
    .success-msg {
        background: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 15px;
        margin: 1rem 0;
        border-left: 6px solid #28a745;
    }
    /* Metrics style */
    .metric-card {
        background: white;
        border-radius: 15px;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #f8f9fa;
    }
    footer {
        visibility: hidden;
    }
</style>
""", unsafe_allow_html=True)

# Header with branding
st.markdown(f"""
<div class="header-card">
    <div class="brand-name">📊 Jakkula Abhishek</div>
    <div class="brand-email">✉️ Jakkulaabhishek5@gmail.com</div>
    <div class="subtitle">Ultimate Automated GST Report Generator | GSTR-1 & GSTR-3B to Excel + Dashboard</div>
</div>
""", unsafe_allow_html=True)

# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================
if 'processed_gstr3b' not in st.session_state:
    st.session_state.processed_gstr3b = {}
if 'processed_gstr1' not in st.session_state:
    st.session_state.processed_gstr1 = {}
if 'processing_log' not in st.session_state:
    st.session_state.processing_log = []
if 'excel_3b_bytes' not in st.session_state:
    st.session_state.excel_3b_bytes = None
if 'excel_1_bytes' not in st.session_state:
    st.session_state.excel_1_bytes = None

# =============================================================================
# HELPER FUNCTIONS - MONTH DETECTION
# =============================================================================
@st.cache_data(ttl=3600)
def extract_month_from_text(text: str) -> Optional[str]:
    """
    Extract month-year in format 'MMYYYY' from PDF text using multiple patterns.
    Returns None if not found.
    """
    patterns = [
        # "Tax period December 2023", "Return Period April 2024"
        r'(?:Tax|Return)\s*period\s*[:]?\s*([A-Za-z]+)\s*(\d{4})',
        # "Period: December 2023"
        r'Period\s*[:]?\s*([A-Za-z]+)\s*(\d{4})',
        # "Month: December 2023"
        r'Month\s*[:]?\s*([A-Za-z]+)\s*(\d{4})',
        # "Dec-2023", "Dec 2023"
        r'([A-Za-z]+)[\s-](\d{4})',
        # "12/2023", "12-2023"
        r'(\d{2})[/-](\d{4})',
        # "122023" (standalone 6 digits)
        r'\b(0[1-9]|1[0-2])(20\d{2})\b',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            groups = match.groups()
            if len(groups) == 2:
                # If first group is month name
                if groups[0].isalpha():
                    month_map = {
                        'january':'01','february':'02','march':'03','april':'04','may':'05','june':'06',
                        'july':'07','august':'08','september':'09','october':'10','november':'11','december':'12',
                        'jan':'01','feb':'02','mar':'03','apr':'04','jun':'06','jul':'07','aug':'08','sep':'09',
                        'oct':'10','nov':'11','dec':'12'
                    }
                    month_num = month_map.get(groups[0].lower(), None)
                    if month_num:
                        return f"{month_num}{groups[1]}"
                # If both are numeric (MM YYYY)
                elif groups[0].isdigit() and groups[1].isdigit():
                    return f"{groups[0]}{groups[1]}"
            elif len(groups) == 1 and groups[0].isdigit() and len(groups[0]) == 6:
                return groups[0]
    return None

# =============================================================================
# GSTR-3B PARSING (Enhanced)
# =============================================================================
def parse_gstr3b(pdf_file) -> Dict[str, Any]:
    """
    Parse a single GSTR-3B PDF and extract all relevant data.
    Returns dictionary with month and numeric values.
    """
    data = {
        "month": None,
        "outward_taxable_value": 0.0,
        "outward_central_tax": 0.0,
        "outward_state_tax": 0.0,
        "outward_integrated_tax": 0.0,
        "itc_central": 0.0,
        "itc_state": 0.0,
        "itc_integrated": 0.0,
        "net_payable_cgst": 0.0,
        "net_payable_sgst": 0.0,
        "net_payable_igst": 0.0,
        "itc_reversed_central": 0.0,
        "itc_reversed_state": 0.0,
        "late_fee_cgst": 0.0,
        "late_fee_sgst": 0.0,
        "interest_cgst": 0.0,
        "interest_sgst": 0.0,
    }
    full_text = ""
    
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                full_text += page_text + "\n"
            tables = page.extract_tables()
            if not tables:
                continue
                
            for table in tables:
                if not table:
                    continue
                # Convert to string for keyword search
                table_str = "\n".join(["|".join([str(c or "") for c in row]) for row in table])
                
                # ---------------- 3.1 Outward supplies ----------------
                if "Outward taxable supplies" in table_str and "Total taxable value" in table_str:
                    for row in table:
                        if row and len(row) >= 3:
                            row_label = str(row[1]).lower()
                            # Total Taxable Value
                            if "total taxable value" in row_label:
                                try:
                                    data["outward_taxable_value"] = float(str(row[2]).replace(",", ""))
                                except:
                                    pass
                            # Central Tax
                            elif "central tax" in row_label:
                                try:
                                    data["outward_central_tax"] = float(str(row[2]).replace(",", ""))
                                except:
                                    pass
                            # State Tax
                            elif "state tax" in row_label:
                                try:
                                    data["outward_state_tax"] = float(str(row[2]).replace(",", ""))
                                except:
                                    pass
                            # Integrated Tax
                            elif "integrated tax" in row_label:
                                try:
                                    data["outward_integrated_tax"] = float(str(row[2]).replace(",", ""))
                                except:
                                    pass
                
                # ---------------- 4. Eligible ITC ----------------
                if "Eligible ITC" in table_str and "All other ITC" in table_str:
                    for row in table:
                        if row and "All other ITC" in str(row[1]):
                            if len(row) >= 5:
                                try:
                                    data["itc_integrated"] = float(str(row[2]).replace(",", ""))
                                    data["itc_central"] = float(str(row[3]).replace(",", ""))
                                    data["itc_state"] = float(str(row[4]).replace(",", ""))
                                except:
                                    pass
                
                # ---------------- 4.B ITC Reversed ----------------
                if "ITC Reversed" in table_str:
                    for row in table:
                        if row and "Others" in str(row[1]) and len(row) >= 4:
                            try:
                                data["itc_reversed_central"] = float(str(row[3]).replace(",", ""))
                                data["itc_reversed_state"] = float(str(row[4]).replace(",", ""))
                            except:
                                pass
                
                # ---------------- 5.1 Interest & Late fee ----------------
                if "Interest & late fee" in table_str:
                    for row in table:
                        if row and "Central Tax" in str(row[1]) and "Interest" in table_str:
                            try:
                                data["interest_cgst"] = float(str(row[2]).replace(",", ""))
                            except:
                                pass
                        if row and "State Tax" in str(row[1]) and "Interest" in table_str:
                            try:
                                data["interest_sgst"] = float(str(row[2]).replace(",", ""))
                            except:
                                pass
                        if row and "Late fee" in str(row[1]) and "Central Tax" in str(row[2]):
                            try:
                                data["late_fee_cgst"] = float(str(row[3]).replace(",", ""))
                            except:
                                pass
                        if row and "Late fee" in str(row[1]) and "State/UT Tax" in str(row[2]):
                            try:
                                data["late_fee_sgst"] = float(str(row[3]).replace(",", ""))
                            except:
                                pass
                
                # ---------------- 6.1 Payment of tax ----------------
                if "Payment of tax" in table_str and "Other than reverse charge" in table_str:
                    for row in table:
                        if row and "Central Tax" in str(row[1]) and "Other than reverse charge" in table_str:
                            try:
                                data["net_payable_cgst"] = float(str(row[2]).replace(",", ""))
                            except:
                                pass
                        if row and "State/UT Tax" in str(row[1]) and "Other than reverse charge" in table_str:
                            try:
                                data["net_payable_sgst"] = float(str(row[2]).replace(",", ""))
                            except:
                                pass
                        if row and "Integrated Tax" in str(row[1]) and "Other than reverse charge" in table_str:
                            try:
                                data["net_payable_igst"] = float(str(row[2]).replace(",", ""))
                            except:
                                pass

    # Extract month from full text
    month = extract_month_from_text(full_text)
    data["month"] = month if month else "unknown"
    return data

# =============================================================================
# GSTR-1 PARSING (Enhanced with more fields)
# =============================================================================
def parse_gstr1(pdf_file) -> Dict[str, Any]:
    """
    Parse a single GSTR-1 PDF and extract B2B invoices, CDNR, HSN, exports, B2CL, etc.
    """
    result = {
        "month": None,
        "b2b": [],
        "cdnr": [],
        "hsn": [],
        "doc_issued": 0,
        "b2cl": [],
        "exports": [],
        "b2cs": [],
    }
    full_text = ""
    
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                full_text += page_text + "\n"
            tables = page.extract_tables()
            if not tables:
                continue
                
            for table in tables:
                if not table:
                    continue
                table_str = "\n".join(["|".join([str(c or "") for c in row]) for row in table])
                
                # ---------- B2B Invoices (Table 4A) ----------
                if "GSTIN/UIN of Recipient" in table_str or "Receiver Name" in table_str:
                    # Find header row
                    header_idx = None
                    for i, row in enumerate(table):
                        row_str = " ".join([str(c or "") for c in row])
                        if "GSTIN/UIN of Recipient" in row_str or "Receiver Name" in row_str:
                            header_idx = i
                            break
                    if header_idx is not None:
                        headers = [str(c or "").strip() for c in table[header_idx]]
                        idx_gstin = next((i for i, h in enumerate(headers) if "GSTIN" in h or "Recipient" in h), None)
                        idx_name = next((i for i, h in enumerate(headers) if "Receiver Name" in h or "Name" in h), None)
                        idx_taxable = next((i for i, h in enumerate(headers) if "Taxable Value" in h), None)
                        idx_cgst = next((i for i, h in enumerate(headers) if "CGST" in h), None)
                        idx_sgst = next((i for i, h in enumerate(headers) if "SGST" in h or "State Tax" in h), None)
                        idx_igst = next((i for i, h in enumerate(headers) if "IGST" in h), None)
                        idx_inv_no = next((i for i, h in enumerate(headers) if "Invoice Number" in h), None)
                        idx_inv_date = next((i for i, h in enumerate(headers) if "Invoice Date" in h), None)
                        
                        for row in table[header_idx+1:]:
                            if not any(row):
                                continue
                            inv = {}
                            if idx_gstin is not None:
                                inv["GSTIN/UIN of Recipient"] = str(row[idx_gstin] or "").strip()
                            if idx_name is not None:
                                inv["Receiver Name"] = str(row[idx_name] or "").strip()
                            if idx_taxable is not None:
                                val = str(row[idx_taxable] or "0").replace(",", "")
                                inv["Taxable Value"] = float(val) if val else 0.0
                            if idx_cgst is not None:
                                val = str(row[idx_cgst] or "0").replace(",", "")
                                inv["CGST Amount"] = float(val) if val else 0.0
                            if idx_sgst is not None:
                                val = str(row[idx_sgst] or "0").replace(",", "")
                                inv["SGST Amount"] = float(val) if val else 0.0
                            if idx_igst is not None:
                                val = str(row[idx_igst] or "0").replace(",", "")
                                inv["IGST Amount"] = float(val) if val else 0.0
                            if idx_inv_no is not None:
                                inv["Invoice Number"] = str(row[idx_inv_no] or "").strip()
                            if idx_inv_date is not None:
                                inv["Invoice Date"] = str(row[idx_inv_date] or "").strip()
                            if inv.get("Taxable Value", 0) > 0 or inv.get("GSTIN/UIN of Recipient"):
                                result["b2b"].append(inv)
                
                # ---------- Credit/Debit Notes (Table 9B) ----------
                if "Credit / Debit notes" in table_str:
                    for row in table:
                        if len(row) > 5 and "CREDIT" in str(row[5]).upper():
                            cdn = {
                                "Note/Refund Voucher Number": str(row[3] or "").strip(),
                                "Note/Refund Voucher date": str(row[4] or "").strip(),
                                "Document Type": "CREDIT",
                                "Taxable Value": 0.0
                            }
                            val = str(row[12] if len(row) > 12 else "0").replace(",", "")
                            try:
                                cdn["Taxable Value"] = float(val)
                            except:
                                pass
                            result["cdnr"].append(cdn)
                        elif len(row) > 5 and "DEBIT" in str(row[5]).upper():
                            cdn = {
                                "Note/Refund Voucher Number": str(row[3] or "").strip(),
                                "Note/Refund Voucher date": str(row[4] or "").strip(),
                                "Document Type": "DEBIT",
                                "Taxable Value": 0.0
                            }
                            val = str(row[12] if len(row) > 12 else "0").replace(",", "")
                            try:
                                cdn["Taxable Value"] = float(val)
                            except:
                                pass
                            result["cdnr"].append(cdn)
                
                # ---------- HSN Summary (Table 12) ----------
                if "HSN-wise summary" in table_str:
                    for row in table:
                        if row and len(row) > 2 and str(row[0]).strip().isdigit() and len(str(row[0]).strip()) >= 4:
                            hsn_row = {
                                "HSN": str(row[0]).strip(),
                                "Total Value": 0.0,
                                "Taxable Value": 0.0,
                                "CGST Amount": 0.0,
                                "SGST Amount": 0.0,
                                "IGST Amount": 0.0
                            }
                            try:
                                hsn_row["Total Value"] = float(str(row[2] or "0").replace(",", ""))
                            except:
                                pass
                            try:
                                hsn_row["Taxable Value"] = float(str(row[5] if len(row)>5 else "0").replace(",", ""))
                            except:
                                pass
                            try:
                                hsn_row["CGST Amount"] = float(str(row[7] if len(row)>7 else "0").replace(",", ""))
                            except:
                                pass
                            try:
                                hsn_row["SGST Amount"] = float(str(row[8] if len(row)>8 else "0").replace(",", ""))
                            except:
                                pass
                            try:
                                hsn_row["IGST Amount"] = float(str(row[6] if len(row)>6 else "0").replace(",", ""))
                            except:
                                pass
                            result["hsn"].append(hsn_row)
                
                # ---------- Documents Issued (Table 13) ----------
                if "Documents issued" in table_str:
                    for row in table:
                        if row and "Net issued" in str(row):
                            try:
                                result["doc_issued"] = int(float(str(row[-1]).replace(",", "")))
                            except:
                                pass
                
                # ---------- B2CL (Large) Table 5 ----------
                if "Taxable outward inter-state supplies made to unregistered persons" in table_str:
                    # Simplified extraction: just count rows or extract totals
                    for row in table:
                        if row and len(row) > 3 and "Total" in str(row[0]):
                            try:
                                val = float(str(row[3] or "0").replace(",", ""))
                                result["b2cl"].append({"Taxable Value": val})
                            except:
                                pass
                
                # ---------- Exports Table 6A ----------
                if "Exports (with/without payment)" in table_str:
                    for row in table:
                        if row and "Total" in str(row[0]) and len(row) > 3:
                            try:
                                val = float(str(row[3] or "0").replace(",", ""))
                                result["exports"].append({"Taxable Value": val})
                            except:
                                pass
                
                # ---------- B2CS (Others) Table 7 ----------
                if "Taxable supplies to unregistered persons" in table_str:
                    for row in table:
                        if row and "Total" in str(row[0]) and len(row) > 3:
                            try:
                                val = float(str(row[3] or "0").replace(",", ""))
                                result["b2cs"].append({"Taxable Value": val})
                            except:
                                pass

    month = extract_month_from_text(full_text)
    result["month"] = month if month else "unknown"
    return result

# =============================================================================
# EXCEL GENERATION (Enhanced)
# =============================================================================
def build_gstr3b_excel(months_data: Dict[str, Dict]) -> bytes:
    """Create multi-month GSTR-3B Excel with additional computed columns."""
    rows = []
    for month, d in sorted(months_data.items()):
        rows.append({
            "Month": month,
            "Outward Taxable Value": d.get("outward_taxable_value", 0),
            "Outward CGST": d.get("outward_central_tax", 0),
            "Outward SGST": d.get("outward_state_tax", 0),
            "Outward IGST": d.get("outward_integrated_tax", 0),
            "ITC CGST": d.get("itc_central", 0),
            "ITC SGST": d.get("itc_state", 0),
            "ITC IGST": d.get("itc_integrated", 0),
            "ITC Reversed CGST": d.get("itc_reversed_central", 0),
            "ITC Reversed SGST": d.get("itc_reversed_state", 0),
            "Net Payable CGST": d.get("net_payable_cgst", 0),
            "Net Payable SGST": d.get("net_payable_sgst", 0),
            "Net Payable IGST": d.get("net_payable_igst", 0),
            "Interest CGST": d.get("interest_cgst", 0),
            "Interest SGST": d.get("interest_sgst", 0),
            "Late Fee CGST": d.get("late_fee_cgst", 0),
            "Late Fee SGST": d.get("late_fee_sgst", 0),
        })
    df = pd.DataFrame(rows)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="GSTR 3B", index=False)
        # Add a summary sheet with totals
        totals = pd.DataFrame([{
            "Total Outward Taxable": df["Outward Taxable Value"].sum(),
            "Total CGST Payable": df["Outward CGST"].sum(),
            "Total SGST Payable": df["Outward SGST"].sum(),
            "Total ITC Availed CGST": df["ITC CGST"].sum(),
            "Total ITC Availed SGST": df["ITC SGST"].sum(),
            "Net CGST Liability": (df["Outward CGST"].sum() - df["ITC CGST"].sum()),
            "Net SGST Liability": (df["Outward SGST"].sum() - df["ITC SGST"].sum()),
        }])
        totals.to_excel(writer, sheet_name="Summary", index=False)
    return output.getvalue()

def build_gstr1_excel(all_data: Dict[str, Dict]) -> bytes:
    """Create combined GSTR-1 Excel with multiple sheets."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Summary sheet
        summary = []
        for month, data in all_data.items():
            total_taxable = sum(inv.get("Taxable Value", 0) for inv in data["b2b"])
            total_cgst = sum(inv.get("CGST Amount", 0) for inv in data["b2b"])
            total_sgst = sum(inv.get("SGST Amount", 0) for inv in data["b2b"])
            total_igst = sum(inv.get("IGST Amount", 0) for inv in data["b2b"])
            summary.append({
                "Return period": month,
                "Filing status": "FILED",
                "Section name": "B2B",
                "Number of documents": len(data["b2b"]),
                "Taxable Value": total_taxable,
                "CGST Amount": total_cgst,
                "SGST Amount": total_sgst,
                "IGST Amount": total_igst,
                "Net Documents Issued": data.get("doc_issued", 0),
            })
        if summary:
            pd.DataFrame(summary).to_excel(writer, sheet_name="summary", index=False)
        
        # B2B sheet
        all_b2b = []
        for month, data in all_data.items():
            for inv in data["b2b"]:
                inv_copy = inv.copy()
                inv_copy["Return period"] = month
                all_b2b.append(inv_copy)
        if all_b2b:
            df_b2b = pd.DataFrame(all_b2b)
            cols = ["Return period", "Invoice Number", "Invoice Date", "GSTIN/UIN of Recipient",
                    "Receiver Name", "Taxable Value", "CGST Amount", "SGST Amount", "IGST Amount"]
            df_b2b = df_b2b[[c for c in cols if c in df_b2b.columns]]
            df_b2b.to_excel(writer, sheet_name="b2b", index=False)
        
        # CDNR sheet
        all_cdnr = []
        for month, data in all_data.items():
            for cdn in data["cdnr"]:
                cdn_copy = cdn.copy()
                cdn_copy["Return period"] = month
                all_cdnr.append(cdn_copy)
        if all_cdnr:
            pd.DataFrame(all_cdnr).to_excel(writer, sheet_name="cdnr", index=False)
        
        # HSN sheet
        all_hsn = []
        for month, data in all_data.items():
            for hsn in data["hsn"]:
                hsn_copy = hsn.copy()
                hsn_copy["Return period"] = month
                all_hsn.append(hsn_copy)
        if all_hsn:
            pd.DataFrame(all_hsn).to_excel(writer, sheet_name="hsn", index=False)
        
        # Docs sheet
        docs = [{"Return period": m, "Net issued": d.get("doc_issued", 0)} for m, d in all_data.items()]
        if docs:
            pd.DataFrame(docs).to_excel(writer, sheet_name="docs", index=False)
        
        # B2CL sheet (if any)
        all_b2cl = []
        for month, data in all_data.items():
            for item in data.get("b2cl", []):
                item["Return period"] = month
                all_b2cl.append(item)
        if all_b2cl:
            pd.DataFrame(all_b2cl).to_excel(writer, sheet_name="b2cl", index=False)
        
        # Exports sheet (if any)
        all_exp = []
        for month, data in all_data.items():
            for item in data.get("exports", []):
                item["Return period"] = month
                all_exp.append(item)
        if all_exp:
            pd.DataFrame(all_exp).to_excel(writer, sheet_name="exports", index=False)
        
        # B2CS sheet (if any)
        all_b2cs = []
        for month, data in all_data.items():
            for item in data.get("b2cs", []):
                item["Return period"] = month
                all_b2cs.append(item)
        if all_b2cs:
            pd.DataFrame(all_b2cs).to_excel(writer, sheet_name="b2cs", index=False)
    
    return output.getvalue()

# =============================================================================
# DASHBOARD VISUALIZATIONS
# =============================================================================
def show_dashboard(gstr3b_data: Dict, gstr1_data: Dict):
    """Display interactive charts and KPIs."""
    st.markdown("## 📈 Interactive Dashboard")
    
    if gstr3b_data:
        # Create DataFrame for GSTR-3B trends
        df_3b = pd.DataFrame([
            {
                "Month": m,
                "Outward Taxable Value": d["outward_taxable_value"],
                "Net CGST Payable": d["net_payable_cgst"],
                "Net SGST Payable": d["net_payable_sgst"],
                "ITC CGST": d["itc_central"],
                "ITC SGST": d["itc_state"],
            } for m, d in gstr3b_data.items()
        ])
        df_3b = df_3b.sort_values("Month")
        
        # KPI Row
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Outward Taxable Value", f"₹{df_3b['Outward Taxable Value'].sum():,.0f}")
        with col2:
            st.metric("Total Net CGST Payable", f"₹{df_3b['Net CGST Payable'].sum():,.0f}")
        with col3:
            st.metric("Total Net SGST Payable", f"₹{df_3b['Net SGST Payable'].sum():,.0f}")
        with col4:
            st.metric("Total ITC Availed (CGST+SGST)", f"₹{(df_3b['ITC CGST'] + df_3b['ITC SGST']).sum():,.0f}")
        
        # Line chart: Outward Taxable Value over months
        fig1 = px.line(df_3b, x="Month", y="Outward Taxable Value", 
                       title="Monthly Outward Taxable Value", markers=True,
                       labels={"Outward Taxable Value": "Amount (₹)"})
        fig1.update_traces(line_color='#1e3c72', line_width=3)
        st.plotly_chart(fig1, use_container_width=True)
        
        # Bar chart: CGST vs SGST Payable
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=df_3b["Month"], y=df_3b["Net CGST Payable"], name="CGST Payable", marker_color='#2a5298'))
        fig2.add_trace(go.Bar(x=df_3b["Month"], y=df_3b["Net SGST Payable"], name="SGST Payable", marker_color='#1e3c72'))
        fig2.update_layout(title="Monthly CGST vs SGST Payable", barmode='group', xaxis_title="Month", yaxis_title="Amount (₹)")
        st.plotly_chart(fig2, use_container_width=True)
        
        # ITC Utilization
        df_itc = df_3b.melt(id_vars=["Month"], value_vars=["ITC CGST", "ITC SGST"], 
                            var_name="ITC Type", value_name="Amount")
        fig3 = px.area(df_itc, x="Month", y="Amount", color="ITC Type", 
                       title="ITC Availed Trend", groupnorm=None)
        st.plotly_chart(fig3, use_container_width=True)
    
    if gstr1_data:
        # B2B invoices count per month
        b2b_counts = {m: len(d["b2b"]) for m, d in gstr1_data.items()}
        df_b2b = pd.DataFrame(list(b2b_counts.items()), columns=["Month", "Number of B2B Invoices"])
        df_b2b = df_b2b.sort_values("Month")
        fig4 = px.bar(df_b2b, x="Month", y="Number of B2B Invoices", 
                      title="B2B Invoices per Month", color="Number of B2B Invoices",
                      color_continuous_scale="Blues")
        st.plotly_chart(fig4, use_container_width=True)
        
        # HSN summary - top 5 HSN by value (aggregate across months)
        all_hsn = []
        for data in gstr1_data.values():
            all_hsn.extend(data["hsn"])
        if all_hsn:
            df_hsn = pd.DataFrame(all_hsn)
            top_hsn = df_hsn.groupby("HSN")["Taxable Value"].sum().nlargest(5).reset_index()
            fig5 = px.pie(top_hsn, values="Taxable Value", names="HSN", title="Top 5 HSN Codes by Taxable Value")
            st.plotly_chart(fig5, use_container_width=True)

# =============================================================================
# MAIN APP LOGIC
# =============================================================================
def main():
    # Sidebar for settings and info
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/000000/invoice.png", width=80)
        st.markdown("## ⚙️ Settings")
        st.markdown("---")
        st.info("**How it works:**\n\n"
                "1. Upload GSTR-1 and/or GSTR-3B PDFs (any filenames)\n"
                "2. The app auto-detects the tax period from PDF content\n"
                "3. Extracts all tables using pdfplumber\n"
                "4. Generates Excel reports and an interactive dashboard\n"
                "5. Download the reports with one click")
        st.markdown("---")
        st.caption("Developed with ❤️ by Jakkula Abhishek")
        st.caption("📧 Jakkulaabhishek5@gmail.com")
    
    # Main area - two columns for upload
    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown('<div class="upload-card">', unsafe_allow_html=True)
        st.subheader("📄 GSTR-3B PDFs")
        gstr3b_uploads = st.file_uploader("Upload one or more GSTR-3B PDFs", type=["pdf"], accept_multiple_files=True, key="gstr3b")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col_right:
        st.markdown('<div class="upload-card">', unsafe_allow_html=True)
        st.subheader("📄 GSTR-1 PDFs")
        gstr1_uploads = st.file_uploader("Upload one or more GSTR-1 PDFs", type=["pdf"], accept_multiple_files=True, key="gstr1")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Process button
    if st.button("🚀 Generate Reports & Dashboard", use_container_width=True):
        if not gstr3b_uploads and not gstr1_uploads:
            st.error("❌ Please upload at least one PDF file.")
            return
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Process GSTR-3B
        gstr3b_data = {}
        if gstr3b_uploads:
            for idx, file in enumerate(gstr3b_uploads):
                status_text.text(f"Processing GSTR-3B: {file.name} ...")
                try:
                    data = parse_gstr3b(file)
                    if data["month"] and data["month"] != "unknown":
                        gstr3b_data[data["month"]] = data
                        st.session_state.processing_log.append(f"✅ GSTR-3B {file.name} → month {data['month']}")
                    else:
                        st.warning(f"⚠️ Could not detect month in {file.name}. Skipped.")
                        st.session_state.processing_log.append(f"❌ GSTR-3B {file.name} → month detection failed")
                except Exception as e:
                    st.error(f"Error parsing {file.name}: {str(e)}")
                    st.session_state.processing_log.append(f"🔥 Error in {file.name}: {str(e)}")
                progress_bar.progress((idx+1)/len(gstr3b_uploads) * 0.5)
        
        # Process GSTR-1
        gstr1_data = {}
        if gstr1_uploads:
            for idx, file in enumerate(gstr1_uploads):
                status_text.text(f"Processing GSTR-1: {file.name} ...")
                try:
                    data = parse_gstr1(file)
                    if data["month"] and data["month"] != "unknown":
                        gstr1_data[data["month"]] = data
                        st.session_state.processing_log.append(f"✅ GSTR-1 {file.name} → month {data['month']}")
                    else:
                        st.warning(f"⚠️ Could not detect month in {file.name}. Skipped.")
                        st.session_state.processing_log.append(f"❌ GSTR-1 {file.name} → month detection failed")
                except Exception as e:
                    st.error(f"Error parsing {file.name}: {str(e)}")
                    st.session_state.processing_log.append(f"🔥 Error in {file.name}: {str(e)}")
                progress_bar.progress(0.5 + (idx+1)/len(gstr1_uploads) * 0.5)
        
        progress_bar.progress(1.0)
        status_text.text("✅ Processing complete!")
        
        # Store in session state
        st.session_state.processed_gstr3b = gstr3b_data
        st.session_state.processed_gstr1 = gstr1_data
        
        # Generate Excel files
        if gstr3b_data:
            st.session_state.excel_3b_bytes = build_gstr3b_excel(gstr3b_data)
        if gstr1_data:
            st.session_state.excel_1_bytes = build_gstr1_excel(gstr1_data)
        
        # Success message
        st.markdown('<div class="success-msg">🎉 Reports generated successfully! You can now download the Excel files and view the dashboard below.</div>', unsafe_allow_html=True)
    
    # Download buttons
    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        if st.session_state.excel_3b_bytes:
            st.download_button(
                label="📥 Download GSTR-3B Multi-Month Excel",
                data=st.session_state.excel_3b_bytes,
                file_name="GSTR3B_Multi_Month.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
    with col_dl2:
        if st.session_state.excel_1_bytes:
            st.download_button(
                label="📥 Download GSTR-1 Combined Excel",
                data=st.session_state.excel_1_bytes,
                file_name="GSTR1_COMBINED.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
    
    # Show dashboard if data exists
    if st.session_state.processed_gstr3b or st.session_state.processed_gstr1:
        show_dashboard(st.session_state.processed_gstr3b, st.session_state.processed_gstr1)
        
        # Show processing log
        with st.expander("📋 Processing Log"):
            for log in st.session_state.processing_log:
                st.write(log)
    
    # Footer
    st.markdown("---")
    st.markdown("<center><small>© 2025 Jakkula Abhishek | Automated GST Reporting Tool | Version 3.0</small></center>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
