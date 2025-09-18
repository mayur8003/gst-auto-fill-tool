import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="GST Auto-Fill Template Tool", layout="wide")
st.title("📥 Auto-Fill GST Template from Books & GST Data (Combined Tabs)")

# ---------------------------
# Template Columns
# ---------------------------
template_columns = [
    "GSTIN/UIN OF RECIPIENT","RECEIVER NAME","INVOICE NO","INVOICE DATE",
    "INVOICE VALUE","PLACE OF SUPPLY","INVOICE TYPE","TAXABLE VALUE",
    "INTEGRATED TAX","CENTRAL TAX","STATE/UT TAX","IRN NUMBER"
]

# ---------------------------
# Books Column Mapping
# ---------------------------
books_column_map = {
    "GSTIN/UIN OF RECIPIENT": ["Original Customer Billing GSTIN", "Customer GSTIN", "GSTIN", "My GSTIN"],
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

# ---------------------------
# GST Column Mapping
# ---------------------------
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
def read_file(uploaded_file, sheet_name=None):
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file, dtype=str)
    else:
        df = pd.read_excel(uploaded_file, sheet_name=sheet_name, dtype=str)
    df.columns = df.columns.str.strip().str.upper()
    return df

def map_columns(df, column_map):
    mapped_df = pd.DataFrame(columns=template_columns)
    df_cols_upper = {col.upper(): col for col in df.columns}
    for template_col, possible_cols in column_map.items():
        for col in possible_cols:
            if col.upper() in df_cols_upper:
                mapped_df[template_col] = df[df_cols_upper[col.upper()]]
                break
        else:
            mapped_df[template_col] = ""
    return mapped_df

def preprocess_df(df):
    for col in ["INVOICE VALUE","TAXABLE VALUE","INTEGRATED TAX","CENTRAL TAX","STATE/UT TAX"]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df["INVOICE DATE"] = pd.to_datetime(df["INVOICE DATE"], errors='coerce').dt.strftime('%d-%m-%Y')
    return df

# ---------------------------
# File Upload
# ---------------------------
st.subheader("Upload Files")
books_file = st.file_uploader("Upload Books Data (Excel/CSV)", type=["xlsx","xls","csv"])
gst_file = st.file_uploader("Upload GST Portal Data (Excel/CSV with multiple sheets)", type=["xlsx","xls","csv"])

# ---------------------------
# Process Books Data
# ---------------------------
if books_file:
    books_df = read_file(books_file)
    books_template_df = map_columns(books_df, books_column_map)
    books_template_df = preprocess_df(books_template_df)

    output_books = BytesIO()
    with pd.ExcelWriter(output_books, engine="openpyxl") as writer:
        books_template_df.to_excel(writer, index=False, sheet_name="Books_Template")
    output_books.seek(0)

    st.download_button(
        "📥 Download Books Auto-Filled Template",
        output_books,
        "Books_AutoFilled_Template.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ---------------------------
# Process GST Portal Data (multi-sheet combined)
# ---------------------------
if gst_file:
    gst_xl = pd.ExcelFile(gst_file)
    sheet_names = gst_xl.sheet_names
    selected_sheets = st.multiselect("Select GST Sheets to Auto-Fill", sheet_names)

    combined_gst_df = pd.DataFrame(columns=template_columns)

    for sheet in selected_sheets:
        gst_df = read_file(gst_file, sheet_name=sheet)
        gst_template_df = map_columns(gst_df, gst_column_map)
        gst_template_df = preprocess_df(gst_template_df)
        combined_gst_df = pd.concat([combined_gst_df, gst_template_df], ignore_index=True)

    if not combined_gst_df.empty:
        output_gst = BytesIO()
        with pd.ExcelWriter(output_gst, engine="openpyxl") as writer:
            combined_gst_df.to_excel(writer, index=False, sheet_name="GST_Combined_Template")
        output_gst.seek(0)

        st.download_button(
            "📥 Download Combined GST Auto-Filled Template",
            output_gst,
            "GST_AutoFilled_Combined_Template.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

st.info("Upload Books and/or GST data above. You can select multiple GST sheets; all selected tabs will be combined into a single template.")
