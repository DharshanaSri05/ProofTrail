# ProofTrail – Document Verification and Audit Analytics

ProofTrail is a web application that helps users upload, track, and verify documents. It detects duplicate files, checks expiry dates, and displays document statistics through an interactive dashboard.

## Features

- **Document Upload:** Upload PDF and image files.
- **Duplicate Detection:** Uses SHA-256 hashing to detect identical files.
- **Expiry Validation:** Flags expired documents as Needs Review.
- **Document Search:** Search using Document ID or file name.
- **Dashboard:** View document statistics, charts, and issue counts.
- **CSV Export:** Download document reports for further analysis.
- **Data Storage:** Uses SQLite to store document records.

## Technologies Used

- Python
- Streamlit
- Pandas
- SQLite
- SHA-256 Hashing
- GitHub

## How to Run Locally

1. Clone this repository.
2. Install the required libraries.
3. Run the application.

```bash
pip install streamlit pandas
streamlit run app.py
```

## Live Demo

[Open ProofTrail](prooftrail-dharshana-test
.streamlit.app)

## Project Purpose

This project demonstrates document management, file integrity checking, expiry validation, database operations, and interactive data analytics.

## Author

Dharshana Sri
