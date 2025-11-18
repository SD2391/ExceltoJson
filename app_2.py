# app.py
import streamlit as st
import pdfplumber
import json
import pandas as pd
from typing import Any
from datetime import datetime
import uuid
from supabase import create_client, Client

# -----------------------------
# Initialize Supabase
# -----------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Import mapping function (make sure mapping_v1.py has run_mapping(input_json: dict) -> dict)
from mapping_v1 import run_mapping

# -----------------------------
# Helper functions (from your existing app)
# -----------------------------
def normalize_color(color) -> tuple:
    if not color or not isinstance(color, (list, tuple)):
        return (1.0, 1.0, 1.0)
    if len(color) == 1:
        gray = float(color[0])
        return (gray, gray, gray)
    elif len(color) == 3:
        return (float(color[0]), float(color[1]), float(color[2]))
    elif len(color) == 4:
        c, m, y, k = float(color[0]), float(color[1]), float(color[2]), float(color[3])
        r = (1 - c) * (1 - k)
        g = (1 - m) * (1 - k)
        b = (1 - y) * (1 - k)
        return (r, g, b)
    return (1.0, 1.0, 1.0)

def is_highlighted_color(color) -> bool:
    r, g, b = normalize_color(color)
    is_white = r > 0.85 and g > 0.85 and b > 0.85
    is_black = r < 0.15 and g < 0.15 and b < 0.15
    return not is_white and not is_black

def detect_header_row_visual(page, table_obj) -> int:
    if not table_obj:
        return -1
    try:
        table_bbox = table_obj.bbox
        x0, top, x1, bottom = table_bbox
        rects = page.within_bbox((x0, top, x1, bottom)).rects
        chars = page.within_bbox((x0, top, x1, bottom)).chars
        if not rects or not chars:
            return -1
        table_rows = table_obj.rows
        if not table_rows:
            return -1
        row_boundaries = []
        for row in table_rows[:5]:
            if row.cells:
                cells = [c for c in row.cells if c]
                if cells:
                    first_cell = cells[0]
                    if hasattr(first_cell, 'bbox'):
                        _, row_top, _, row_bottom = first_cell.bbox
                        row_boundaries.append((row_top, row_bottom))
                    elif isinstance(first_cell, (list, tuple)) and len(first_cell) >= 4:
                        row_top = first_cell[1]
                        row_bottom = first_cell[3]
                        row_boundaries.append((row_top, row_bottom))
        if not row_boundaries:
            return -1
        row_highlights: dict[int, int] = {}
        for rect in rects:
            rect_top = rect.get('top', 0)
            rect_bottom = rect.get('bottom', 0)
            rect_mid = (rect_top + rect_bottom) / 2
            for row_idx, (r_top, r_bottom) in enumerate(row_boundaries):
                if r_top <= rect_mid <= r_bottom:
                    fill_color = rect.get('non_stroking_color')
                    if fill_color and is_highlighted_color(fill_color):
                        row_highlights[row_idx] = row_highlights.get(row_idx, 0) + 1
                    break
        for row_idx in sorted(row_highlights.keys()):
            if row_highlights[row_idx] >= 1:
                r_top, r_bottom = row_boundaries[row_idx]
                has_text = any(r_top <= char.get('top', 0) <= r_bottom for char in chars)
                if has_text:
                    return row_idx
    except Exception:
        pass
    return -1

def is_likely_header_row(row) -> bool:
    if not row:
        return False
    non_empty_cells = [cell for cell in row if cell is not None and str(cell).strip()]
    if len(non_empty_cells) < len(row) * 0.5:
        return False
    text_cells = 0
    short_text_cells = 0
    for cell in non_empty_cells:
        cell_str = str(cell).strip()
        is_number = cell_str.replace('.', '').replace('-', '').replace(',', '').replace('$', '').replace('%', '').isdigit()
        if not is_number:
            text_cells += 1
            if len(cell_str.split()) <= 5:
                short_text_cells += 1
    has_mostly_text = text_cells >= len(non_empty_cells) * 0.7 if non_empty_cells else False
    has_short_text = short_text_cells >= len(non_empty_cells) * 0.6 if non_empty_cells else False
    return has_mostly_text and has_short_text

def detect_multirow_headers(table: list, start_idx: int) -> tuple[int, list[str]]:
    if start_idx >= len(table):
        return start_idx, table[start_idx] if start_idx < len(table) else []
    potential_header_rows = []
    max_header_rows = min(3, len(table) - start_idx)
    for i in range(max_header_rows):
        row = table[start_idx + i]
        if is_likely_header_row(row):
            potential_header_rows.append(row)
        else:
            break
    if len(potential_header_rows) <= 1:
        return start_idx, table[start_idx] if start_idx < len(table) else []
    num_cols = max(len(row) for row in potential_header_rows)
    consolidated_headers = []
    for col_idx in range(num_cols):
        header_parts = []
        for row in potential_header_rows:
            if col_idx < len(row) and row[col_idx] is not None:
                cell_str = str(row[col_idx]).strip()
                if cell_str and cell_str not in header_parts:
                    header_parts.append(cell_str)
        if header_parts:
            consolidated_headers.append(' '.join(header_parts))
        else:
            consolidated_headers.append(None)
    return start_idx + len(potential_header_rows) - 1, consolidated_headers

def detect_header_row(table: list, page=None, table_obj=None) -> int:
    if not table or len(table) == 0:
        return 0
    if page and table_obj:
        visual_header = detect_header_row_visual(page, table_obj)
        if visual_header >= 0 and visual_header < len(table):
            candidate_row = table[visual_header]
            if is_likely_header_row(candidate_row):
                return visual_header
    max_rows_to_check = min(5, len(table))
    for idx, row in enumerate(table[:max_rows_to_check]):
        if is_likely_header_row(row):
            return idx
    return 0

def infer_column_types(data_rows: list[list], num_cols: int) -> list[str]:
    column_types = ['text'] * num_cols
    for col_idx in range(num_cols):
        sample_values = []
        for row in data_rows[:min(10, len(data_rows))]:
            if col_idx < len(row) and row[col_idx] is not None:
                val = str(row[col_idx]).strip()
                if val:
                    sample_values.append(val)
        if not sample_values:
            continue
        numeric_count = 0
        date_count = 0
        for val in sample_values:
            clean_val = val.replace(',', '').replace('$', '').replace('%', '').replace(' ', '')
            if clean_val.replace('.', '').replace('-', '').isdigit():
                numeric_count += 1
            elif '/' in val or '-' in val:
                parts = val.replace('/', '-').split('-')
                if len(parts) >= 2 and all(p.isdigit() for p in parts):
                    date_count += 1
        if numeric_count >= len(sample_values) * 0.7:
            column_types[col_idx] = 'numeric'
        elif date_count >= len(sample_values) * 0.7:
            column_types[col_idx] = 'date'
    return column_types

def clean_table_data(table: list, page=None, table_obj=None) -> tuple[list[str], list[list]]:
    if not table or len(table) == 0:
        return [], []
    header_idx = detect_header_row(table, page, table_obj)
    final_header_idx, raw_headers = detect_multirow_headers(table, header_idx)
    all_data_rows = table[final_header_idx + 1:] if final_header_idx + 1 < len(table) else []
    data_rows = []
    for row in all_data_rows:
        if row and any(cell is not None and str(cell).strip() for cell in row):
            data_rows.append(row)
    clean_headers = []
    header_counts: dict[str, int] = {}
    for i, header in enumerate(raw_headers):
        if header is None or str(header).strip() == '':
            clean_header = f"Column_{i+1}"
        else:
            clean_header = str(header).strip()
            clean_header = clean_header.replace('\n', ' ').replace('\r', ' ')
            clean_header = ' '.join(clean_header.split())
        if clean_header in header_counts:
            header_counts[clean_header] += 1
            clean_header = f"{clean_header}_{header_counts[clean_header]}"
        else:
            header_counts[clean_header] = 1
        clean_headers.append(clean_header)
    if not clean_headers:
        return [], data_rows
    expected_cols = len(clean_headers)
    normalized_rows = []
    for row in data_rows:
        if not row:
            continue
        if not any(cell is not None and str(cell).strip() for cell in row):
            continue
        current_row = list(row)
        if len(current_row) < expected_cols:
            current_row = current_row + [None] * (expected_cols - len(current_row))
        elif len(current_row) > expected_cols:
            current_row = current_row[:expected_cols]
        cleaned_row = []
        for cell in current_row:
            if cell is None:
                cleaned_row.append(None)
            else:
                cleaned_cell = str(cell).strip()
                cleaned_cell = cleaned_cell.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
                cleaned_cell = ' '.join(cleaned_cell.split())
                cleaned_row.append(cleaned_cell if cleaned_cell else None)
        normalized_rows.append(cleaned_row)
    if normalized_rows and expected_cols > 0:
        column_types = infer_column_types(normalized_rows, expected_cols)
        validated_rows = []
        for row in normalized_rows:
            row_looks_like_header = is_likely_header_row(row)
            if row_looks_like_header:
                continue
            validated_row = []
            for col_idx in range(expected_cols):
                cell = row[col_idx] if col_idx < len(row) else None
                col_type = column_types[col_idx] if col_idx < len(column_types) else 'text'
                if cell is None or str(cell).strip() == '':
                    validated_row.append(cell)
                    continue
                cell_str = str(cell).strip()
                if col_type == 'numeric':
                    clean_val = cell_str.replace(',', '').replace('$', '').replace('%', '').replace(' ', '')
                    if not clean_val.replace('.', '').replace('-', '').isdigit():
                        validated_row.append(None)
                    else:
                        validated_row.append(cell)
                elif col_type == 'date':
                    parts = cell_str.replace('/', '-').split('-')
                    if len(parts) >= 2 and all(p.strip().isdigit() for p in parts if p.strip()):
                        validated_row.append(cell)
                    else:
                        validated_row.append(None)
                else:
                    validated_row.append(cell)
            if any(cell is not None and str(cell).strip() for cell in validated_row):
                validated_rows.append(validated_row)
        normalized_rows = validated_rows if validated_rows else normalized_rows
    return clean_headers, normalized_rows

def filter_null_values(data: list[dict]) -> list[dict]:
    filtered_data = []
    for record in data:
        filtered_record = {}
        for k, v in record.items():
            if v is None:
                continue
            if pd.isna(v):
                continue
            if isinstance(v, str) and str(v).strip() == '':
                continue
            filtered_record[k] = v
        if filtered_record:
            filtered_data.append(filtered_record)
    return filtered_data

# -----------------------------
# Streamlit app UI
# -----------------------------
st.set_page_config(page_title="PDF → Mapping → History", page_icon="📄", layout="wide")
st.title("📄 PDF Extractor → Mapping → History")

# Initialize session state flags (prevent duplicate inserts)
if 'uploaded_once' not in st.session_state:
    st.session_state['uploaded_once'] = False
if 'last_uploaded_filename' not in st.session_state:
    st.session_state['last_uploaded_filename'] = None

# Initialize session state history (keeps UI history for session; DB holds full history)
if 'history' not in st.session_state:
    st.session_state['history'] = []

tabs = st.tabs(["Upload", "History"])

# -----------------------------
# Upload tab
# -----------------------------
with tabs[0]:
    st.header("Upload PDF")
    uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"], help="Upload a PDF to extract and map")

    extraction_type = st.radio("Extraction type:", options=["Tables", "Text", "Both"], horizontal=True)

    # Reset the uploaded_once flag only when a new file is uploaded (filename changed)
    if uploaded_file:
        if st.session_state.get('last_uploaded_filename') != uploaded_file.name:
            st.session_state['last_uploaded_filename'] = uploaded_file.name
            st.session_state['uploaded_once'] = False

    if uploaded_file is not None and not st.session_state['uploaded_once']:
        try:
            with pdfplumber.open(uploaded_file) as pdf:
                total_pages = len(pdf.pages)
                st.success(f"✅ PDF loaded — {total_pages} page(s).")
                all_data: dict[str, Any] = {
                    "metadata": {
                        "filename": uploaded_file.name,
                        "total_pages": total_pages
                    },
                    "pages": []
                }

                progress_text = st.empty()
                for page_num, page in enumerate(pdf.pages, start=1):
                    progress_text.text(f"Processing page {page_num} / {total_pages}...")
                    page_data: dict[str, Any] = {"page_number": page_num}

                    if extraction_type in ["Tables", "Both"]:
                        table_settings = page.find_tables()
                        if table_settings:
                            page_data["tables"] = []
                            for table_idx, table_obj in enumerate(table_settings):
                                try:
                                    table = table_obj.extract()
                                    if table and len(table) > 0:
                                        clean_headers, normalized_rows = clean_table_data(table, page, table_obj)
                                        if clean_headers and normalized_rows:
                                            df = pd.DataFrame(normalized_rows, columns=clean_headers)  # type: ignore
                                            raw_data = df.to_dict(orient="records")
                                            filtered_data = filter_null_values(raw_data)
                                            if filtered_data:
                                                page_data["tables"].append({
                                                    "table_number": table_idx + 1,
                                                    "data": filtered_data
                                                })
                                        elif normalized_rows:
                                            df = pd.DataFrame(normalized_rows)
                                            raw_data = df.to_dict(orient="records")
                                            filtered_data = filter_null_values(raw_data)
                                            if filtered_data:
                                                page_data["tables"].append({
                                                    "table_number": table_idx + 1,
                                                    "data": filtered_data
                                                })
                                except Exception:
                                    pass
                    if extraction_type in ["Text", "Both"]:
                        text = page.extract_text()
                        if text:
                            page_data["text"] = text
                    if len(page_data) > 1:
                        all_data["pages"].append(page_data)
                progress_text.empty()

                if not all_data["pages"]:
                    st.warning("No structured data found in the PDF.")
                # Prepare JSON strings
                raw_json_obj = all_data
                raw_json_str = json.dumps(raw_json_obj, indent=2, ensure_ascii=False)
                compact_raw_json = json.dumps(raw_json_obj, ensure_ascii=False)

                # Run mapping (call to mapping_v1.run_mapping)
                mapped_json_obj = {}
                try:
                    with st.spinner("Running mapping_v1 on extracted JSON..."):
                        mapped_json_obj = run_mapping(raw_json_obj) or {}
                except Exception as e:
                    st.error(f"Mapping function raised an error: {e}")
                    mapped_json_obj = {}

                mapped_json_str = json.dumps(mapped_json_obj, indent=2, ensure_ascii=False)
                compact_mapped_json = json.dumps(mapped_json_obj, ensure_ascii=False)

                # Display split view: left - extracted preview, right - mapped JSON
                left_col, right_col = st.columns(2)

                with left_col:
                    st.subheader("📋 Extracted Data Preview")
                    if all_data["pages"]:
                        for page in all_data["pages"][:3]:
                            with st.expander(f"Page {page['page_number']}", expanded=page['page_number'] == 1):
                                if "tables" in page:
                                    st.write(f"**Tables found:** {len(page['tables'])}")
                                    for table in page["tables"]:
                                        st.write(f"Table {table['table_number']}:")
                                        st.dataframe(pd.DataFrame(table["data"]), use_container_width=True)
                                if "text" in page:
                                    st.text_area(f"Text from page {page['page_number']}", page["text"], height=200, key=f"text_{page['page_number']}")
                        if len(all_data["pages"]) > 3:
                            st.info(f"Showing first 3 pages. All pages are included in the downloadable JSON.")
                    else:
                        st.warning("No data extracted to preview.") 

                with right_col:
                    st.subheader("🔄 Mapped JSON (mapping_v1 output)")
                    if mapped_json_obj:
                        st.code(mapped_json_str, language="json", line_numbers=True)
                    else:
                        st.info("Mapping returned empty result or failed. You can still download raw JSON below.")

                st.divider()

                # Downloads and save to history
                col1, col2, col3 = st.columns([1,1,2])
                with col1:
                    st.download_button(
                        label="📥 Download Raw JSON",
                        data=compact_raw_json,
                        file_name=f"{uploaded_file.name.rsplit('.',1)[0]}.json",
                        mime="application/json",
                        use_container_width=True
                    )
                with col2:
                    st.download_button(
                        label="📥 Download Mapped JSON",
                        data=compact_mapped_json,
                        file_name=f"{uploaded_file.name.rsplit('.',1)[0]}_mapped.json",
                        mime="application/json",
                        use_container_width=True
                    )
                with col3:
                    st.info(f"Pages with data: {len(all_data['pages'])} | Tables extracted: {sum(len(p.get('tables', [])) for p in all_data['pages'])}")

                # Save record to Supabase (insert once per upload)
                with st.spinner("Saving record to Supabase..."):
                    supabase.table("pdf_history").insert({
                        "filename": uploaded_file.name,
                        "raw_json": raw_json_obj,
                        "mapped_json": mapped_json_obj,
                        "page_count": len(raw_json_obj.get("pages", [])),
                        "table_count": sum(len(p.get("tables", [])) for p in raw_json_obj.get("pages", [])),
                        "mapped_keys": len(mapped_json_obj.keys()),
                        "is_deleted": False
                    }).execute()

                # Mark as processed so subsequent reruns (downloads, clicks) won't insert again
                st.session_state['uploaded_once'] = True
                st.success("Saved to History (visible in the History tab).")

        except Exception as e:
            st.error(f"❌ Error processing PDF: {e}")

# -----------------------------
# History tab
# -----------------------------
with tabs[1]:
    # ---------------------------
    # HEADER + DELETE ALL BUTTON
    # ---------------------------
    col1, col2 = st.columns([7, 1])
    with col1:
        st.header("📁 History")
    with col2:
        if st.button("🗑️ Delete All"):
            supabase.table("pdf_history") \
                .update({"is_deleted": True}) \
                .eq("is_deleted", False) \
                .execute()
            st.success("All records moved to deleted state.")
            st.rerun()

    # ---------------------------
    # FETCH ONLY NON-DELETED ROWS
    # ---------------------------
    result = (
        supabase.table("pdf_history")
        .select("*")
        .eq("is_deleted", False)
        .order("uploaded_at", desc=True)
        .execute()
    )
    rows = result.data

    if not rows:
        st.info("No history records available.")
    else:
        st.subheader("📊 History Table")

        # ---------------------------
        # TABLE HEADER
        # ---------------------------
        header_cols = st.columns([2, 2, 1, 1, 1, 1, 1, 1])
        headers = [
            "Filename", "Uploaded At", "Pages", "Tables",
            "Mapped Keys", "Raw JSON", "Mapped JSON", "Delete"
        ]
        for col, h in zip(header_cols, headers):
            col.markdown(f"**{h}**")

        st.write("---")

        # ---------------------------
        # TABLE ROWS
        # ---------------------------
        for row in rows:
            c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([2, 2, 1, 1, 1, 1, 1, 1])

            c1.write(row["filename"])
            c2.write(row["uploaded_at"])
            c3.write(row["page_count"])
            c4.write(row["table_count"])
            c5.write(row["mapped_keys"])

            # RAW DOWNLOAD
            c6.download_button(
                "⬇",
                data=json.dumps(row["raw_json"], ensure_ascii=False),
                file_name=f"{row['filename'].split('.')[0]}_raw.json",
                key=f"raw_{row['id']}",
            )

            # MAPPED DOWNLOAD
            c7.download_button(
                "⬇",
                data=json.dumps(row["mapped_json"], ensure_ascii=False),
                file_name=f"{row['filename'].split('.')[0]}_mapped.json",
                key=f"mapped_{row['id']}",
            )

            # DELETE ROW (SOFT DELETE)
            if c8.button("❌", key=f"del_{row['id']}"):
                supabase.table("pdf_history") \
                    .update({"is_deleted": True}) \
                    .eq("id", row["id"]) \
                    .execute()
                st.success("Deleted successfully.")
                st.rerun()

        st.write("---")
