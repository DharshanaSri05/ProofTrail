
import streamlit as st
import pandas as pd
import hashlib
import sqlite3
from pathlib import Path
from datetime import date

st.set_page_config(
    page_title="ProofTrail",
    layout="wide"
)

st.title("ProofTrail")
st.subheader("Document Quality and Audit Analytics")
st.write(
    "Upload documents and check for duplicate files "
    "and expired dates."
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

DB_PATH = "prooftrail.db"


# Create the database table
def initialize_database():
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT NOT NULL,
                document_type TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_hash TEXT NOT NULL UNIQUE,
                expiry_date TEXT,
                status TEXT NOT NULL,
                issue TEXT NOT NULL
            )
        """)


# Load documents from SQLite
def load_documents():
    with sqlite3.connect(DB_PATH) as connection:
        documents = pd.read_sql_query("""
            SELECT
                document_id AS 'Document ID',
                document_type AS 'Document Type',
                file_name AS 'File Name',
                file_hash AS 'File Hash',
                COALESCE(expiry_date, 'Not provided')
                    AS 'Expiry Date',
                status AS 'Status',
                issue AS 'Issue'
            FROM documents
            ORDER BY id DESC
        """, connection)

    return documents


# Initialize the database
initialize_database()


# Document upload form
with st.form("upload_form"):
    document_id = st.text_input("Document ID")

    document_type = st.selectbox(
        "Document type",
        ["Invoice", "Certificate", "Business Report", "Other"],
        key="upload_document_type"
    )

    expiry_date = st.date_input(
        "Expiry date (optional)",
        value=None
    )

    uploaded_files = st.file_uploader(
        "Upload PDF or image files",
        type=["pdf", "png", "jpg", "jpeg"],
        accept_multiple_files=True
    )

    submitted = st.form_submit_button("Upload documents")


# Process uploaded documents
if submitted:
    if not document_id.strip():
        st.error("Please enter a Document ID.")

    elif not uploaded_files:
        st.error("Please select at least one file.")

    else:
        saved_count = 0

        for uploaded_file in uploaded_files:
            file_bytes = uploaded_file.getvalue()
            file_hash = hashlib.sha256(file_bytes).hexdigest()

            # Check for duplicate files
            with sqlite3.connect(DB_PATH) as connection:
                existing = connection.execute(
                    "SELECT 1 FROM documents WHERE file_hash = ?",
                    (file_hash,)
                ).fetchone()

            if existing is not None:
                st.warning(
                    f"{uploaded_file.name}: "
                    "this file was already uploaded."
                )
                continue

            # Save the file locally
            safe_name = Path(uploaded_file.name).name
            destination = (
                UPLOAD_DIR / f"{file_hash[:12]}_{safe_name}"
            )
            destination.write_bytes(file_bytes)

            # Check expiry date
            issue = "None"
            status = "Complete"

            if expiry_date and expiry_date < date.today():
                issue = "Expired"
                status = "Needs Review"

            # Save document details in SQLite
            try:
                with sqlite3.connect(DB_PATH) as connection:
                    connection.execute("""
                        INSERT INTO documents (
                            document_id,
                            document_type,
                            file_name,
                            file_hash,
                            expiry_date,
                            status,
                            issue
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        document_id.strip(),
                        document_type,
                        uploaded_file.name,
                        file_hash,
                        (
                            str(expiry_date)
                            if expiry_date
                            else None
                        ),
                        status,
                        issue
                    ))

                saved_count += 1

            except sqlite3.IntegrityError:
                st.warning(
                    f"{uploaded_file.name}: "
                    "this file was already uploaded."
                )

        if saved_count:
            st.success(
                f"Uploaded {saved_count} document(s)."
            )


# Load saved records
documents = load_documents()

st.divider()
st.subheader("Document Quality Summary")


if documents.empty:
    st.info(
        "No documents uploaded yet. "
        "Upload a document to view your analytics."
    )

else:
    # Filters
    filter_col1, filter_col2 = st.columns(2)

    with filter_col1:
        document_type_filter = st.selectbox(
            "Filter by Document Type",
            ["All"] + sorted(
                documents["Document Type"].unique().tolist()
            ),
            key="document_type_filter"
        )

    with filter_col2:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All"] + sorted(
                documents["Status"].unique().tolist()
            ),
            key="status_filter"
        )

    # Apply selected filters
    
    # Apply selected filters
    filtered_documents = documents.copy()

    # Search by Document ID or File Name
    search_query = st.text_input(
        "Search Documents",
        placeholder="Enter Document ID or File Name...",
        key="document_search"
    )

    if search_query.strip():
        search_text = search_query.strip()

        matches = (
            filtered_documents["Document ID"]
            .str.contains(search_text, case=False, na=False, regex=False)
            |
            filtered_documents["File Name"]
            .str.contains(search_text, case=False, na=False, regex=False)
        )

        filtered_documents = filtered_documents[matches]

    if document_type_filter != "All":
        filtered_documents = filtered_documents[
            filtered_documents["Document Type"]
            == document_type_filter
        ]

    if status_filter != "All":
        filtered_documents = filtered_documents[
            filtered_documents["Status"] == status_filter
        ]

    # Convert expiry dates into dates
    expiry_dates = pd.to_datetime(
    filtered_documents["Expiry Date"],
    format="%Y-%m-%d",
    errors="coerce"
)    # Summary metrics
    total = len(filtered_documents)

    issues = int(
        (filtered_documents["Issue"] == "Expired").sum()
    )

    issue_rate = (
        issues / total * 100
        if total > 0
        else 0
    )

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Documents", total)
    col2.metric("Documents With Issues", issues)
    col3.metric("Issue Rate", f"{issue_rate:.1f}%")

    # Chart 1: Documents by type
    st.subheader("Documents by Type")

    type_counts = (
        filtered_documents["Document Type"]
        .value_counts()
        .rename_axis("Document Type")
        .reset_index(name="Count")
    )

    if not type_counts.empty:
        st.bar_chart(
            type_counts,
            x="Document Type",
            y="Count",
            x_label="Document Type",
            y_label="Number of Documents"
        )
    else:
        st.info("No documents match the selected filters.")

    # Chart 2: Expired vs Valid Documents
    st.subheader("Expired vs Valid Documents")

    expired_count = int(
        (expiry_dates < pd.Timestamp(date.today())).sum()
    )

    valid_count = int(
        (expiry_dates.dt.date >= date.today()).sum()
    )

    no_expiry_count = int(expiry_dates.isna().sum())

    expiry_summary = pd.DataFrame({
        "Expiry Status": [
            "Expired",
            "Valid",
            "No Expiry Date"
        ],
        "Count": [
            expired_count,
            valid_count,
            no_expiry_count
        ]
    })

    st.bar_chart(
        expiry_summary,
        x="Expiry Status",
        y="Count",
        x_label="Expiry Status",
        y_label="Number of Documents"
    )

    # Chart 3: Document status
    st.subheader("Document Status Analysis")

    status_counts = (
        filtered_documents["Status"]
        .value_counts()
        .rename_axis("Status")
        .reset_index(name="Count")
    )

    if not status_counts.empty:
        st.bar_chart(
            status_counts,
            x="Status",
            y="Count",
            x_label="Document Status",
            y_label="Number of Documents"
        )

    # Document table
    st.subheader("Uploaded Documents")

    display_documents = filtered_documents.drop(
        columns=["File Hash"]
    ).copy()

    display_documents["Issue"] = (
        display_documents["Issue"].fillna("None")
    )

    st.dataframe(
        display_documents,
        width="stretch"
    )

    # Export filtered records to CSV
    csv_data = display_documents.to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        "Download CSV Report",
        data=csv_data,
        file_name="prooftrail_report.csv",
        mime="text/csv"
    )


st.caption(
    "ProofTrail prototype: records are stored in a local SQLite "
    "database, and uploaded files are saved in the uploads folder."
)
