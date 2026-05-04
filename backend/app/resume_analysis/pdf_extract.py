import fitz


def extract_text_from_pdf(file_bytes: bytes) -> str:
    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        parts: list[str] = []
        for page in doc:
            parts.append(page.get_text())
    return "\n".join(parts).strip()
