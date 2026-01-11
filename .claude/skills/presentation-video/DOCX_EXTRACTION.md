# DOCX Text Extraction

This document explains how to extract text content from Microsoft Word (.docx) files for use as context in voiceover script generation.

## Why Extract DOCX?

Word documents often contain:
- Book summaries and key concepts
- Source material for presentations
- Detailed explanations and examples
- Case studies and stories

This content enriches voiceover scripts with specific examples and deeper context.

## Extraction Method

DOCX files are ZIP archives containing XML. The main text is in `word/document.xml`.

### Python Script

Use [scripts/extract_docx.py](scripts/extract_docx.py) or this inline approach:

```python
import zipfile
from xml.etree import ElementTree

def extract_docx_text(docx_path):
    """Extract plain text from a .docx file."""
    with zipfile.ZipFile(docx_path, 'r') as docx:
        xml_content = docx.read('word/document.xml')
        tree = ElementTree.fromstring(xml_content)

        # Word XML namespace
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

        texts = []
        for elem in tree.iter():
            if elem.tag == '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t':
                if elem.text:
                    texts.append(elem.text)

        return ' '.join(texts)

# Usage
content = extract_docx_text('ReWork.docx')
print(content)
```

### Bash One-Liner

```bash
python -c "
import zipfile
from xml.etree import ElementTree
with zipfile.ZipFile('document.docx', 'r') as docx:
    tree = ElementTree.fromstring(docx.read('word/document.xml'))
    print(' '.join(e.text for e in tree.iter() if e.tag.endswith('}t') and e.text))
"
```

## Output Format

The extracted text is plain text with:
- All formatting removed
- Paragraphs joined with spaces
- Headers and body text concatenated

This is sufficient for context analysis - we don't need formatting for voiceover generation.

## Integration with Skill

When the presentation-video skill encounters a `.docx` file:

1. Extract text using the method above
2. Analyze content for:
   - Key concepts and themes
   - Specific examples and case studies
   - Memorable quotes and statistics
   - Story arcs and narrative structure
3. Use extracted content to enrich voiceover scripts

## Example

**Input**: `ReWork.docx` (book summary)

**Extracted themes**:
- "You need less than you think to start"
- "Launch immediately, don't wait for perfection"
- "Make a stand for something you care about"

**Extracted examples**:
- 37signals/Basecamp - launched without billing
- Vinnie's Sub Shop - stops selling when bread isn't fresh
- Zappos - customer service obsession
- Nike waffle sole - Bill Bowerman's innovation

These get incorporated into the voiceover script for richer narration.
