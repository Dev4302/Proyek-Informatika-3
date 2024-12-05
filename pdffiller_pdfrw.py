import re
from pdfrw import PdfReader, PdfWriter, IndirectPdfDict

# Function to clean field names, removing BOM and unwanted characters
def clean_field_name(field_name):
    try:
        cleaned_name = field_name.encode('latin1').decode('utf-16')
    except UnicodeDecodeError:
        cleaned_name = field_name.encode('latin1').decode('utf-8', 'ignore')

    cleaned_name = re.sub(r'[^\w\s]', '', cleaned_name)
    
    return cleaned_name.strip()

def fill_pdf(input_pdf_path, output_pdf_path, data_dict):
    template_pdf = PdfReader(input_pdf_path)
    annotations = template_pdf.pages[0]['/Annots']

    # Iterate semua field
    for annotation in annotations:
        if annotation['/Subtype'] == '/Widget' and annotation['/T']:
            field_name = annotation['/T'][1:-1]  #ambil nama field (remove parentheses)
            cleaned_field_name = clean_field_name(field_name)  # Clean the field name
            
            print(f"Attempting to fill field: '{cleaned_field_name}'")  # Debugging line

            # Check nama field ada di data fill/ data_dict
            if cleaned_field_name in data_dict:
                print(f"Filling {cleaned_field_name} with value: {data_dict[cleaned_field_name]}")  # Debugging line
                annotation.update(
                    IndirectPdfDict(V='{}'.format(data_dict[cleaned_field_name]))  # isi field
                )

    # Save the filled PDF
    PdfWriter(output_pdf_path, trailer=template_pdf).write()

# Example data to fill in the form fields
data_to_fill = {
    'f1_10': 'ivan',  
    'f1_20': 'timotius',
    'f1_30': 'Example Text',
    'f1_40': 'More Text'
    #tinggal tambahin disini
}

input_pdf_path = 'C:/Users/Lenovo/Desktop/Semester 9/Proyek Informatika/PDF filler py/Proyek-Informatika-3/f1040ez--2016.pdf'
output_pdf_path = 'C:/Users/Lenovo/Desktop/Semester 9/Proyek Informatika/PDF filler py/Proyek-Informatika-3/output_pdfs/output_f104.pdf'

fill_pdf(input_pdf_path, output_pdf_path, data_to_fill)

print(f"PDF filled and saved as {output_pdf_path}")
