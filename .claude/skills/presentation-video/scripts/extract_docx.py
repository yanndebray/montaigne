#!/usr/bin/env python3
"""
Extract plain text from Microsoft Word (.docx) files.

Usage:
    python extract_docx.py <docx_file>
    python extract_docx.py ReWork.docx > output.txt
"""

import sys
import zipfile
from xml.etree import ElementTree


def extract_docx_text(docx_path: str) -> str:
    """
    Extract plain text from a .docx file.

    DOCX files are ZIP archives containing XML. The main document
    text is stored in word/document.xml.

    Args:
        docx_path: Path to the .docx file

    Returns:
        Extracted plain text with paragraphs joined by spaces
    """
    with zipfile.ZipFile(docx_path, 'r') as docx:
        # Read the main document XML
        xml_content = docx.read('word/document.xml')
        tree = ElementTree.fromstring(xml_content)

        # Word XML namespace for text elements
        word_ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

        # Extract all text elements
        texts = []
        for elem in tree.iter():
            # <w:t> elements contain text content
            if elem.tag == f'{word_ns}t':
                if elem.text:
                    texts.append(elem.text)

        return ' '.join(texts)


def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_docx.py <docx_file>", file=sys.stderr)
        sys.exit(1)

    docx_path = sys.argv[1]

    try:
        text = extract_docx_text(docx_path)
        print(text)
    except FileNotFoundError:
        print(f"Error: File not found: {docx_path}", file=sys.stderr)
        sys.exit(1)
    except zipfile.BadZipFile:
        print(f"Error: Invalid .docx file: {docx_path}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
