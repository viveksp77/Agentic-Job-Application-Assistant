import PyPDF2
from typing import Optional

def parse_resume_pdf(file_path: str) -> Optional[str]:
    """Extract text from PDF resume file.
    
    Args:
        file_path: Path to PDF file
        
    Returns:
        Extracted text or None if error
    """
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ''
            for page in pdf_reader.pages:
                text += page.extract_text() + '\n'
        return text.strip()
    except Exception as e:
        print(f"Error parsing PDF: {e}")
        return None

