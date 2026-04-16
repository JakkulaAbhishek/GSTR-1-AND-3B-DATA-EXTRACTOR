"""
================================================================================
GST Report Generator - Fully Automated & Robust
================================================================================
Author   : Jakkula Abhishek
Email    : Jakkulaabhishek5@gmail.com
Version  : 4.0 (Fixed PDF Extraction + Animated Background)
================================================================================
"""

import streamlit as st
import pandas as pd
import pdfplumber
import re
import io
from typing import Dict, Any, Optional
import warnings
warnings.filterwarnings('ignore')

# =============================================================================
# PAGE CONFIG & ANIMATED BACKGROUND
# =============================================================================
st.set_page_config(page_title="GST Report Generator", page_icon="📊", layout="wide")

# Animated gradient background (light, elegant)
st.markdown("""
<style>
@keyframes gradient {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
.stApp {
    background: linear-gradient(-45deg, #f8f9fa, #e9ecef, #dee2e6, #f8f9fa);
    background-size: 400% 400%;
    animation: gradient 15s ease infinite;
}
.main .block-container {
    background: rgba(255,255,255,0.85);
    border-radius: 30px;
    padding: 2rem;
    backdrop-filter: blur(5px);
    box-shadow: 0 8px 20px rgba(0,0,0,0.05);
}
.header-card {
    background: linear-gradient(135deg, #1e3c72, #2a5298);
    border-radius: 25px;
    padding: 1.8rem;
    text-align: center;
    color: white;
    margin-bottom: 2rem;
}
.brand-name { font-size: 2.5rem; font-weight: 800; }
.brand-email { font-size: 1.1rem; opacity: 0.9; }
.upload-card {
    background: white;
    border-radius: 20px;
    padding: 1.5rem;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    transition: 0.3s;
}
.upload-card:hover { transform: translateY(-5px); }
.stButton > button {
    background: linear-gradient(90deg, #1e3c72, #2a5298);
    color: white;
    border-radius: 40px;
    font-weight: 600;
}
.success-msg {
    background: #d4edda;
    color: #155724;
    padding: 1rem;
    border-radius: 15px;
    border-left: 6px solid #28a745;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header-card">
    <div class="brand-name">📊 Jakkula Abhishek</div>
    <div class="brand-email">✉️ Jakkulaabhishek5@gmail.com</div>
    <div style="font-size:1rem; margin-top:0.5rem;">Ultimate Automated GST Report Generator</div>
</div>
""", unsafe_allow_html=True)

# =============================================================================
# SESSION STATE
# =============================================================================
if 'gstr3b_data' not in st.session_state:
    st.session_state.gstr3b_data = {}
if 'gstr1_data' not in st.session_state:
    st.session_state.gstr1_data = {}
if 'log' not in st.session_state:
    st.session_state.log = []

# =============================================================================
# HELPER: EXTRACT MONTH FROM TEXT
# =============================================================================
def extract_month_year(text: str) -> Optional[str]:
    patterns = [
        r'(?:Tax|Return)\s*period\s*[:]?\s*([A-Za-z]+)\s*(\d{4})',
        r'Period\s*[:]?\s*([A-Za-z]+)\s*(\d{4})',
        r'(\d{2})/(\d{4})', r'(\d{2})-(\d{4})',
        r'\b(0[1-9]|1[0-2])(20\d{2})\b'
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            if len(m.groups()) == 2:
                if m.group(1).isalpha():
                    month_map = {'jan':'01','feb':'02','mar':'03','apr':'04','may':'05','jun':'06',
                                 'jul':'07','aug':'08','sep':'09','oct':'10','nov':'11','dec':'12'}
                    month_num = month_map.get(m.group(1)[:3].lower())
                    if month_num:
                        return f"{month_num}{m.group(2)}"
                else:
                    return f"{m.group(1)}{m.group(2)}"
            elif len(m.groups()) == 1 and len(m.group(0)) == 6:
                return m.group(0)
    return None

# =============================================================================
# GSTR-3B PARSING (ROBUST)
# =============================================================================
def parse_gstr3b(pdf_file) -> Dict[str, Any]:
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
    }
    full_text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"
            tables = page.extract_tables()
            for table in tables:
                if not table:
                    continue
                # Convert to list of rows for easier access
                for row_idx, row in enumerate(table):
                    if not row:
                        continue
                    row_text = " ".join([str(cell or "") for cell in row]).lower()
                    # ---- Outward supplies row (a) ----
                    if "(a) outward taxable supplies" in row_text or "outward taxable supplies" in row_text:
                        # Find numbers in the row (taxable value, CGST, SGST, IGST)
                        numbers = re.findall(r'[\d,]+\.?\d*', " ".join([str(cell or "") for cell in row]))
                        if len(numbers) >= 5:
                            try:
                                data["outward_taxable_value"] = float(numbers[0].replace(",", ""))
                                data["outward_integrated_tax"] = float(numbers[1].replace(",", ""))
                                data["outward_central_tax"] = float(numbers[2].replace(",", ""))
                                data["outward_state_tax"] = float(numbers[3].replace(",", ""))
                            except:
                                pass
                    # ---- All other ITC row ----
                    if "all other itc" in row_text:
                        numbers = re.findall(r'[\d,]+\.?\d*', " ".join([str(cell or "") for cell in row]))
                        if len(numbers) >= 3:
                            try:
                                data["itc_integrated"] = float(numbers[0].replace(",", ""))
                                data["itc_central"] = float(numbers[1].replace(",", ""))
                                data["itc_state"] = float(numbers[2].replace(",", ""))
                            except:
                                pass
                    # ---- Payment of tax: Central Tax (Other than reverse charge) ----
                    if "central tax" in row_text and "other than reverse charge" in row_text:
                        numbers = re.findall(r'[\d,]+\.?\d*', " ".join([str(cell or "") for cell in row]))
                        if numbers:
                            try:
                                data["net_payable_cgst"] = float(numbers[0].replace(",", ""))
                            except:
                                pass
                    if "state/ut tax" in row_text and "other than reverse charge" in row_text:
                        numbers = re.findall(r'[\d,]+\.?\d*', " ".join([str(cell or "") for cell in row]))
                        if numbers:
                            try:
                                data["net_payable_sgst"] = float(numbers[0].replace(",", ""))
                            except:
                                pass
                    if "integrated tax" in row_text and "other than reverse charge" in row_text:
                        numbers = re.findall(r'[\d,]+\.?\d*', " ".join([str(cell or "") for cell in row]))
                        if numbers:
                            try:
                                data["net_payable_igst"] = float(numbers[0].replace(",", ""))
                            except:
                                pass
    month = extract_month_year(full_text)
    data["month"] = month if month else "unknown"
    return data

# =============================================================================
# GSTR-1 PARSING (ROBUST)
# =============================================================================
def parse_gstr1(pdf_file) -> Dict[str, Any]:
    result = {
        "month": None,
        "b2b": [],
        "cdnr": [],
        "hsn": [],
        "doc_issued": 0,
    }
    full_text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"
            tables = page.extract_tables()
            for table in tables:
                if not table:
                    continue
                # Find header row for B2B (contains "GSTIN/UIN of Recipient")
                header_idx = None
                for i, row in enumerate(table):
                    row_str = " ".join([str(c or "") for c in row])
                    if "GSTIN/UIN of Recipient" in row_str or "Receiver Name" in row_str:
                        header_idx = i
                        break
                if header_idx is not None:
                    headers = [str(c or "").strip() for c in table[header_idx]]
                    # Indices
                    idx_gstin = next((i for i, h in enumerate(headers) if "GSTIN" in h or "Recipient" in h), None)
                    idx_name = next((i for i, h in enumerate(headers) if "Receiver Name" in h or "Name" in h), None)
                    idx_taxable = next((i for i, h in enumerate(headers) if "Taxable Value" in h), None)
                    idx_cgst = next((i for i, h in enumerate(headers) if "CGST" in h), None)
                    idx_sgst = next((i for i, h in enumerate(headers) if "SGST" in h), None)
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
                # Credit/Debit Notes
                if "Credit / Debit notes" in str(table):
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
                # HSN
                if "HSN-wise summary" in str(table):
                    for row in table:
                        if row and len(row) > 2 and str(row[0]).strip().isdigit() and len(str(row[0]).strip()) >= 4:
                            hsn_row = {
                                "HSN": str(row[0]).strip(),
                                "Taxable Value": 0.0,
                                "CGST Amount": 0.0,
                                "SGST Amount": 0.0,
                            }
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
                            result["hsn"].append(hsn_row)
                # Documents issued
                if "Documents issued" in str(table):
                    for row in table:
                        if row and "Net issued" in str(row):
                            try:
                                result["doc_issued"] = int(float(str(row[-1]).replace(",", "")))
                            except:
                                pass
    month = extract_month_year(full_text)
    result["month"] = month if month else "unknown"
    return result

# =============================================================================
# EXCEL BUILDERS (unchanged but ensure no errors)
# =============================================================================
def build_gstr3b_excel(data: Dict) -> bytes:
    rows = []
    for m, d in data.items():
        rows.append({
            "Month": m,
            "Outward Taxable Value": d.get("outward_taxable_value", 0),
            "Outward CGST": d.get("outward_central_tax", 0),
            "Outward SGST": d.get("outward_state_tax", 0),
            "Outward IGST": d.get("outward_integrated_tax", 0),
            "ITC CGST": d.get("itc_central", 0),
            "ITC SGST": d.get("itc_state", 0),
            "ITC IGST": d.get("itc_integrated", 0),
            "Net Payable CGST": d.get("net_payable_cgst", 0),
            "Net Payable SGST": d.get("net_payable_sgst", 0),
            "Net Payable IGST": d.get("net_payable_igst", 0),
        })
    df = pd.DataFrame(rows)
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="GSTR 3B", index=False)
        totals = pd.DataFrame([{
            "Total Outward": df["Outward Taxable Value"].sum(),
            "Total CGST": df["Outward CGST"].sum(),
            "Total SGST": df["Outward SGST"].sum(),
            "Net CGST Liability": df["Outward CGST"].sum() - df["ITC CGST"].sum(),
            "Net SGST Liability": df["Outward SGST"].sum() - df["ITC SGST"].sum(),
        }])
        totals.to_excel(writer, sheet_name="Summary", index=False)
    return out.getvalue()

def build_gstr1_excel(data: Dict) -> bytes:
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        # Summary
        summ = []
        for m, d in data.items():
            total_taxable = sum(i.get("Taxable Value",0) for i in d["b2b"])
            total_cgst = sum(i.get("CGST Amount",0) for i in d["b2b"])
            total_sgst = sum(i.get("SGST Amount",0) for i in d["b2b"])
            summ.append({
                "Return period": m, "Filing status": "FILED", "Section name": "B2B",
                "Number of documents": len(d["b2b"]), "Taxable Value": total_taxable,
                "CGST Amount": total_cgst, "SGST Amount": total_sgst
            })
        if summ:
            pd.DataFrame(summ).to_excel(writer, sheet_name="summary", index=False)
        # B2B
        all_b2b = []
        for m, d in data.items():
            for inv in d["b2b"]:
                inv["Return period"] = m
                all_b2b.append(inv)
        if all_b2b:
            pd.DataFrame(all_b2b).to_excel(writer, sheet_name="b2b", index=False)
        # CDNR
        all_cdnr = []
        for m, d in data.items():
            for c in d["cdnr"]:
                c["Return period"] = m
                all_cdnr.append(c)
        if all_cdnr:
            pd.DataFrame(all_cdnr).to_excel(writer, sheet_name="cdnr", index=False)
        # HSN
        all_hsn = []
        for m, d in data.items():
            for h in d["hsn"]:
                h["Return period"] = m
                all_hsn.append(h)
        if all_hsn:
            pd.DataFrame(all_hsn).to_excel(writer, sheet_name="hsn", index=False)
        # Docs
        docs = [{"Return period": m, "Net issued": d.get("doc_issued",0)} for m,d in data.items()]
        if docs:
            pd.DataFrame(docs).to_excel(writer, sheet_name="docs", index=False)
    return out.getvalue()

# =============================================================================
# MAIN APP
# =============================================================================
def main():
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="upload-card">', unsafe_allow_html=True)
        st.subheader("📄 GSTR-3B PDFs")
        g3_files = st.file_uploader("Upload", type=["pdf"], accept_multiple_files=True, key="g3")
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="upload-card">', unsafe_allow_html=True)
        st.subheader("📄 GSTR-1 PDFs")
        g1_files = st.file_uploader("Upload", type=["pdf"], accept_multiple_files=True, key="g1")
        st.markdown('</div>', unsafe_allow_html=True)

    if st.button("🚀 Generate Reports", use_container_width=True):
        if not g3_files and not g1_files:
            st.error("Please upload at least one PDF.")
            return

        prog = st.progress(0)
        status = st.empty()
        g3_data, g1_data = {}, {}

        # Process GSTR-3B
        if g3_files:
            for i, f in enumerate(g3_files):
                status.text(f"Processing GSTR-3B: {f.name}")
                try:
                    d = parse_gstr3b(f)
                    if d["month"] and d["month"] != "unknown":
                        g3_data[d["month"]] = d
                        st.session_state.log.append(f"✅ {f.name} → {d['month']}")
                    else:
                        st.warning(f"Month not detected in {f.name}")
                except Exception as e:
                    st.error(f"Error in {f.name}: {e}")
                prog.progress((i+1)/len(g3_files) * 0.5)
        # Process GSTR-1
        if g1_files:
            for i, f in enumerate(g1_files):
                status.text(f"Processing GSTR-1: {f.name}")
                try:
                    d = parse_gstr1(f)
                    if d["month"] and d["month"] != "unknown":
                        g1_data[d["month"]] = d
                        st.session_state.log.append(f"✅ {f.name} → {d['month']}")
                    else:
                        st.warning(f"Month not detected in {f.name}")
                except Exception as e:
                    st.error(f"Error in {f.name}: {e}")
                prog.progress(0.5 + (i+1)/len(g1_files) * 0.5)

        prog.progress(1.0)
        status.text("✅ Done!")
        st.session_state.gstr3b_data = g3_data
        st.session_state.gstr1_data = g1_data

        if g3_data:
            st.session_state.excel3b = build_gstr3b_excel(g3_data)
        if g1_data:
            st.session_state.excel1 = build_gstr1_excel(g1_data)

        st.markdown('<div class="success-msg">🎉 Reports generated! Download below.</div>', unsafe_allow_html=True)

    # Download buttons
    col_a, col_b = st.columns(2)
    with col_a:
        if 'excel3b' in st.session_state and st.session_state.excel3b:
            st.download_button("📥 GSTR-3B Excel", data=st.session_state.excel3b,
                               file_name="GSTR3B_Multi_Month.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    with col_b:
        if 'excel1' in st.session_state and st.session_state.excel1:
            st.download_button("📥 GSTR-1 Excel", data=st.session_state.excel1,
                               file_name="GSTR1_COMBINED.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # Show log
    if st.session_state.log:
        with st.expander("📋 Processing Log"):
            for l in st.session_state.log:
                st.write(l)

if __name__ == "__main__":
    main()
