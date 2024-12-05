from pdfrw import PdfReader, PdfWriter

def fill_pdf(input_pdf_path, output_pdf_path, data):
    # Read the input PDF
    template_pdf = PdfReader(input_pdf_path)
    
    # Loop through the pages of the PDF
    for page in template_pdf.pages:
        annotations = page['/Annots']  # This contains the form fields
        if annotations:
            for annotation in annotations:
                field_name = annotation['/T']
                if field_name:
                    field_name = field_name[1:-1]  # Remove parentheses from field name
                    if field_name in data:
                        # Fill the form field with the corresponding value from 'data'
                        annotation.update(
                            pdfrw.PdfDict(V='{}'.format(data[field_name]), Ff=1)
                        )
    
    # Write the filled PDF to the output path
    PdfWriter(output_pdf_path, trailer=template_pdf).write()

# Data to fill in the PDF (field names and corresponding values)
data = {
    'Name': 'John Doe',
    'Address': '1234 Main St, Cityville',
    'Phone': '555-1234'
}

# Paths to input and output PDFs
input_pdf = r'C:\Users\Lenovo\Desktop\Semester 9\Proyek Informatika\PDF filler py\Proyek-Informatika-3\input.pdf'
output_pdf = r'C:\Users\Lenovo\Desktop\Semester 9\Proyek Informatika\PDF filler py\Proyek-Informatika-3\output.pdf'

# Fill the PDF form
fill_pdf(input_pdf, output_pdf, data)

print("PDF filled and saved as:", output_pdf)
