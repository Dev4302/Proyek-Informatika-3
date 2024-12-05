from pdfrw import PdfReader, PdfWriter, IndirectPdfDict

def fill_pdf(input_pdf_path, output_pdf_path, data_dict):
    template_pdf = PdfReader(input_pdf_path)
    
    annotations = template_pdf.pages[0]['/Annots']
    
    for annotation in annotations:
        if annotation['/Subtype'] == '/Widget' and annotation['/T']:
            key = annotation['/T'][1:-1]  
            if key in data_dict:
                annotation.update(
                    IndirectPdfDict(V='{}'.format(data_dict[key]))
                )
    
    PdfWriter(output_pdf_path, trailer=template_pdf).write()

data_to_fill = {
    'Name': 'tester',
    'ID': '123456789',
    'Income': '50000',
    'Tax_Due': '5000'
}

# Call the function with the path to your PDF form and the output path
fill_pdf('C:/Users/Lenovo/Desktop/Semester 9/Proyek Informatika/PDF filler py/Proyek-Informatika-3/2018_1770S.pdf',
         #'C:/Users/Lenovo/Desktop/Semester 9/Proyek Informatika/PDF filler py/Proyek-Informatika-3/f1040ez--2016'
         'C:/Users/Lenovo/Desktop/Semester 9/Proyek Informatika/PDF filler py/Proyek-Informatika-3/output_pdfs/output.pdf',
         data_to_fill)
