from pdfrw import PdfReader

def extract_field_names(pdf_path):
    # Read the PDF
    reader = PdfReader(pdf_path)

    # Iterate through the pages and extract form field names
    for page in reader.pages:
        annotations = page.get('/Annots')  # Simply access the list directly
        if annotations:
            for annotation in annotations:
                field_name = annotation.get('/T')  # Access the field name
                if field_name:
                    print(f"Field Name: {field_name[1:-1]}")  # Remove parentheses from field name

# Replace this with the path to your PDF file
pdf_path = r"C:\Users\Lenovo\Desktop\Semester 9\Proyek Informatika\PDF filler py\Proyek-Informatika-3\empty-form.pdf"

extract_field_names(pdf_path)
