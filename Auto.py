import streamlit as st
import pandas as pd
from io import BytesIO
import zipfile
import re

st.set_page_config(page_title="GST & Books Auto-Fill Tool", layout="wide")
st.title("📥 Auto-Fill GST & Books Templates (Merged Sheets)")

# ---------------------------
# Template Columns
# ---------------------------
template_columns = [
    "GSTIN/UIN OF RECIPIENT","RECEIVER NAME","INVOICE NO","INVOICE DATE",
    "INVOICE VALUE","PLACE OF SUPPLY","INVOICE TYPE","TAXABLE VALUE",
    "INTEGRATED TAX","CENTRAL TAX","STATE/UT TAX","IRN NUMBER"
]

# ---------------------------
# Column Mappings
# ---------------------------
books_column_map = {
    "GSTIN/UIN OF RECIPIENT": ["Original Customer Billing GSTIN", "Customer GSTIN", "GSTIN", "Customer Billing GSTIN"],
    "RECEIVER NAME": ["Customer Name", "Receiver Name", "Billed To Name", "Customer Billing Name"], 
    "INVOICE NO": ["Original Invoice Number (In case of amendment)", "Invoice Number", "Bill No", "Voucher Number of Linked Advance Receipt", "Document Number"], 
    "INVOICE DATE": ["Original Invoice Date (In case of amendment)", "Invoice Date", "Bill Date", "Date of Linked Advance Receipt", "Document Date"], 
    "INVOICE VALUE": ["Invoice Value", "Total Amount", "Invoice Amt"],
    "PLACE OF SUPPLY": ["Place of Supply", "State", "State Place of Supply"], 
    "INVOICE TYPE": ["Type of Export"], 
    "TAXABLE VALUE": ["Item Taxable Value", "Taxable Amount"],
    "INTEGRATED TAX": ["IGST Amount", "Integrated Tax", "IGST Rate"],
    "CENTRAL TAX": ["CGST Amount", "Central Tax", "CGST Rate"],
    "STATE/UT TAX": ["SGST Amount", "State/UT Tax", "SGST Rate"],
    "IRN NUMBER": ["IRN Number", "IRN"]
}

gst_column_map = {
    "GSTIN/UIN OF RECIPIENT": ["GSTIN/UIN of Recipient"],
    "RECEIVER NAME": ["Receiver Name"],
    "INVOICE NO": ["Invoice number", "Invoice Number", "Note Number"],
    "INVOICE DATE": ["Invoice date", "Invoice Date", "Note Date"],
    "INVOICE VALUE": ["Invoice value", "Invoice Value", "Note value"],
    "PLACE OF SUPPLY": ["Place of Supply"],
    "INVOICE TYPE": ["Invoice Type", "Note Supply Type"],
    "TAXABLE VALUE": ["Taxable Value"],
    "INTEGRATED TAX": ["Integrated Tax"],
    "CENTRAL TAX": ["Central Tax"],
    "STATE/UT TAX": ["State/UT Tax"],
    "IRN NUMBER": ["IRN"]
}

# ---------------------------
# Helper Functions
# ---------------------------
def clean_column_name(col):
    """Clean column names for consistent mapping."""
    if not isinstance(col, str):
        col = str(col)
    col = col.strip()
    col = re.sub(r'\s+', ' ', col)   # replace multiple spaces with single space
    col = re.sub(r'\W', '', col)     # remove non-alphanumeric characters
    return col.upper()

def map_columns(df, column_map):
    """Map any dataframe to template columns, robust to messy headers."""
    mapped_df = pd.DataFrame(columns=template_columns)

    # Clean dataframe columns
    df_cols_clean = {clean_column_name(col): col for col in df.columns}

    for template_col, possible_cols in column_map.items():
        mapped = False
        for col in possible_cols:
            col_clean = clean_column_name(col)
            if col_clean in df_cols_clean:
                mapped_df[template_col] = df[df_cols_clean[col_clean]]
                mapped = True
                break
        if not mapped:
            mapped_df[template_col] = ""
    return mapped_df

def preprocess_df(df):
    """Robust preprocessing for numeric and date columns."""

    # ---- Numeric columns ----
    numeric_cols = ["INVOICE VALUE","TAXABLE VALUE","INTEGRATED TAX","CENTRAL TAX","STATE/UT TAX"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # ---- Date column ----
    if "INVOICE DATE" in df.columns:
        def normalize_date(val):
            if pd.isna(val) or str(val).strip() == "":
                return ""
            val_str = str(val).strip().split(" ")[0]

            # Case 1: Excel serial numbers
            if str(val_str).replace(".", "").isdigit():
                try:
                    return (pd.to_datetime("1899-12-30") 
                            + pd.to_timedelta(int(float(val_str)), unit="D")
                           ).strftime("%d-%m-%Y")
                except:
                    pass

            # Case 2: Try common formats
            for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%d-%b-%Y", "%d-%b-%y", "%Y-%m-%d", "%Y/%m/%d"):
                try:
                    dt = pd.to_datetime(val_str, format=fmt, errors="raise", dayfirst=True)
                    return dt.strftime("%d-%m-%Y")
                except:
                    continue

            # Case 3: Fallback to pandas auto parse
            try:
                return pd.to_datetime(val_str, errors="coerce", dayfirst=True).strftime("%d-%m-%Y")
            except:
                return ""

        df["INVOICE DATE"] = df["INVOICE DATE"].apply(normalize_date)

    return df

# ---------------------------
# File Upload
# ---------------------------
st.subheader("Upload Files")
books_file = st.file_uploader("Upload Books Data (Excel/CSV)", type=["xlsx","xls","csv"])
gst_file = st.file_uploader("Upload GST Portal Data (Excel/CSV with multiple sheets)", type=["xlsx","xls","csv"])

# ---------------------------
# Header Row Inputs
# ---------------------------
books_header_row = st.number_input("Header row for Books file (1-based)", min_value=1, value=1)
gst_header_row = st.number_input("Header row for GST file (1-based)", min_value=1, value=4)

if books_file or gst_file:

    # ---------------- Books Processing ----------------
    if books_file:
        books_xl = pd.ExcelFile(books_file)
        books_sheets = books_xl.sheet_names
        selected_books_sheets = st.multiselect("Select Books Sheets to Auto-Fill", books_sheets, default=books_sheets)

        combined_books_df = pd.DataFrame(columns=template_columns)
        for sheet in selected_books_sheets:
            df = pd.read_excel(books_file, sheet_name=sheet, header=books_header_row-1, dtype=str)
            mapped_df = map_columns(df, books_column_map)
            mapped_df = preprocess_df(mapped_df)
            combined_books_df = pd.concat([combined_books_df, mapped_df], ignore_index=True)

    # ---------------- GST Processing ----------------
    if gst_file:
        gst_xl = pd.ExcelFile(gst_file)
        gst_sheets = gst_xl.sheet_names
        selected_gst_sheets = st.multiselect("Select GST Sheets to Auto-Fill", gst_sheets, default=gst_sheets)

        combined_gst_df = pd.DataFrame(columns=template_columns)
        for sheet in selected_gst_sheets:
            df = pd.read_excel(gst_file, sheet_name=sheet, header=gst_header_row-1, dtype=str)
            mapped_df = map_columns(df, gst_column_map)
            mapped_df = preprocess_df(mapped_df)
            combined_gst_df = pd.concat([combined_gst_df, mapped_df], ignore_index=True)

    # ---------------- Create ZIP ----------------
    if (books_file and not combined_books_df.empty) or (gst_file and not combined_gst_df.empty):
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            if books_file and not combined_books_df.empty:
                books_bytes = BytesIO()
                with pd.ExcelWriter(books_bytes, engine="openpyxl") as writer:
                    combined_books_df.to_excel(writer, index=False, sheet_name="Books_Template")
                books_bytes.seek(0)
                zip_file.writestr("Books_AutoFilled_Template.xlsx", books_bytes.getvalue())

            if gst_file and not combined_gst_df.empty:
                gst_bytes = BytesIO()
                with pd.ExcelWriter(gst_bytes, engine="openpyxl") as writer:
                    combined_gst_df.to_excel(writer, index=False, sheet_name="GST_Combined_Template")
                gst_bytes.seek(0)
                zip_file.writestr("GST_AutoFilled_Combined_Template.xlsx", gst_bytes.getvalue())

        zip_buffer.seek(0)
        st.download_button(
            "📥 Download Both Templates (ZIP)",
            zip_buffer,
            "GST_Books_Templates.zip",
            "application/zip"
        )

st.info("Select one or more sheets from Books and GST files. All selected sheets are merged into a single template per file, then both templates are provided in a ZIP download.")
