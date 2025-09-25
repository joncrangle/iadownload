# Internet Archive PDF Download Script

A Python script for searching and downloading PDF files from the Internet Archive with metadata collection and file size analysis.

## Prerequisites

- **Python 3.8+**

## Usage with uv

```bash
uv sync
uv run iadownload.py
```

The script will guide you through an interactive process:

### 1. Enter Search Query
Use Internet Archive search syntax. Examples:
- `title:("Statutes of the Province of Ontario") AND collection:(ontario_council_university_libraries)`
- `creator:"Ontario" AND mediatype:texts`
- `collection:americana AND date:[1800 TO 1900]`

### 2. Choose Action
- **Option 1**: Check total PDF file size only (no downloads)
- **Option 2**: Download PDFs and create metadata CSV

### 3. Select Download Directory (Option 2 only)
- Press Enter for current directory
- Enter folder name to create/use subdirectory

## Output Files

When downloading (Option 2):
- **PDF files**: Individual PDF files from matching items
- **`internet_archive_metadata.csv`**: Contains metadata for each downloaded file including:
  - ItemID, FileName, title, creator, publisher, date, subject, language, description, call_number

When checking file sizes (Option 1):
- **`filesize_report.csv`** (optional): Size analysis for each item

## Search Query Syntax

The script uses Internet Archive's search syntax:
- `title:"exact title"` - Search by title
- `creator:"author name"` - Search by creator/author
- `collection:collection_name` - Search within specific collection
- `mediatype:texts` - Filter by media type
- `date:[1900 TO 2000]` - Date range search
- `subject:"topic"` - Search by subject

Combine with `AND`, `OR`, `NOT` operators.

## Dependencies

**Core dependencies** (installed automatically):
- `internetarchive>=3.0.0` - Internet Archive CLI and Python library
- `rich>=13.0.0` - Enhanced terminal UI (optional, graceful fallback if missing)

**System requirements**:
- Python 3.8+

## Troubleshooting

**"ia command not found"**: Dependencies not installed. Run `uv sync`

**No rich colors/progress bars**: Script works with graceful fallback if rich is unavailable

**Network timeouts**: Try running the script again - it will skip already downloaded files

**Permission errors**: Ensure write access to the target directory

**Python version errors**: Requires Python 3.8+
