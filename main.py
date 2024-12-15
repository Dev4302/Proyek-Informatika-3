import os
import logging
import argparse
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from pdfrw import PdfReader, PdfWriter, IndirectPdfDict
from faker import Faker
import re

# logging 
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
# ini untuk fine tune, FORM itu jumlah form yg akan dibuat
SINGLE_DEDUCTION = 10350
DOUBLE_DEDUCTION = 20700
TAX_RATE = 0.1
FORM = 1

fake = Faker()

def clean_field_name(field_name):
    try:
        cleaned_name = field_name.encode('latin1').decode('utf-16')
    except UnicodeDecodeError:
        cleaned_name = field_name.encode('latin1').decode('utf-8', 'ignore')

    cleaned_name = re.sub(r'[^\w\s]', '', cleaned_name)
    return cleaned_name.strip()

def get_field(input_pdf_path):
    template_pdf = PdfReader(input_pdf_path)
    annotations = template_pdf.pages[0]['/Annots']
    form_fields = []

    for annotation in annotations:
        if annotation['/Subtype'] == '/Widget' and annotation['/T']:
            field_name = annotation['/T'][1:-1]
            cleaned_field_name = clean_field_name(field_name)
            form_fields.append(cleaned_field_name)
    return form_fields

def random_data_generator(form_fields):
    rand_data = {
        form_fields[0]: fake.first_name(),
        form_fields[1]: fake.last_name(),
        form_fields[2]: fake.ssn().replace('-', ''),
        form_fields[6]: fake.street_address(),
        form_fields[7]: fake.building_number(),
        form_fields[8]: fake.city() + " " + fake.state() + " " + fake.zipcode(),
        form_fields[14]: fake.random_int(min=1000, max=100000),
        form_fields[16]: fake.random_int(min=0, max=1500),
        form_fields[18]: fake.random_int(min=0, max=10000),
        form_fields[24]: SINGLE_DEDUCTION,
        form_fields[28]: fake.random_int(min=0, max=10000),
        form_fields[30]: fake.random_int(min=0, max=2000),
        form_fields[39]: fake.random_int(min=0, max=1000),
        form_fields[46]: fake.random_number(digits=9),
        form_fields[49]: fake.random_number(digits=12),
        form_fields[57]: fake.job(),
        form_fields[58]: fake.phone_number(),
    }

    gross = rand_data[form_fields[14]] + rand_data[form_fields[16]] + rand_data[form_fields[18]]
    taxable_income = max(gross - rand_data[form_fields[24]], 0)
    total_payment = rand_data[form_fields[28]] + rand_data[form_fields[30]]
    tax = taxable_income * TAX_RATE
    total_tax = tax + rand_data[form_fields[39]]
    refund = max(total_payment - total_tax, 0)
    owed = max(total_tax - total_payment, 0)

    cal_field = {
        form_fields[20]: gross,
        form_fields[26]: taxable_income,
        form_fields[34]: total_payment,
        form_fields[36]: tax,
        form_fields[41]: total_tax,
        form_fields[44]: refund,
        form_fields[50]: owed
    }

    rand_data |= cal_field
    return rand_data

def fill_data(template, output, data):
    template_pdf = PdfReader(template)
    annotations = template_pdf.pages[0]['/Annots']

    for annotation in annotations:
        if annotation['/Subtype'] == '/Widget' and annotation['/T']:
            field_name = annotation['/T'][1:-1]
            cleaned_field_name = clean_field_name(field_name)

            if cleaned_field_name in data:
                annotation.update(
                    IndirectPdfDict(V='{}'.format(data[cleaned_field_name]))
                )

    PdfWriter(output, trailer=template_pdf).write()

def process_record(template, output_dir, record_id):
    try:
        record = random_data_generator(get_field(template))
        pdf_name = os.path.join(output_dir, f"form_{record_id+1}.pdf").replace("\\", "/")
        fill_data(template, pdf_name, record)
        logging.info(f"PDF generated: '{pdf_name}'")
        return record
    except Exception as e:
        logging.error(f"Error processing record {record_id+1}: {e}")
        return None

def main(template, output_dir, csv_file, num_records):
    if not os.path.isfile(template):
        raise FileNotFoundError(f"Template file not found: {template}")
    if not os.access(os.path.dirname(output_dir) or ".", os.W_OK):
        raise PermissionError(f"No write access to directory: {output_dir}")

    os.makedirs(output_dir, exist_ok=True)
    logging.info("Starting record generation...")

    with ThreadPoolExecutor() as executor:
        results = list(executor.map(
            lambda i: process_record(template, output_dir, i),
            range(num_records)
        ))

    # menghapus data invalid
    csv_data = [record for record in results if record]

    # proses buat csv
    if csv_data:
        df = pd.DataFrame(csv_data)
         # sebelum diconvert ke csv, tambahin dulu nama kolom nama file disini
        df.insert(0, 'File_name', [f'form_{i+1}.pdf' for i in range(len(df))])
        # ini mapping kolom-kolom pertama dari exctracted pdf
        rename_mapping = {
        "f1_10": "firstname",
        "f1_20": "lastname",
        "f1_30": "ssn",
        "f1_60": "adress",
        "f1_70": "apt no",
        "f1_80": "adress2",
        "f1_120": "wages",
        "f1_140": "interest",
        "f1_160": "un-comp",
        "f1_180": "gross",
        "f1_220": "deduction",
        "f1_300": "taxable-income",
        "f1_320": "withheld",
        "f1_360": "total-tax",
        "f1_380": "refund",
        "f1_420": "owed",
        "f1_470": "occupation",
        "f1_480": "phone",
        "f1_200": "adjusted_gross_income",
        "f1_240": "tax",
        "f1_260": "total_payments",
        "f1_340": "total_income",
        "f1_400": "refund",
        "f1_410": "amount_owed"
        }
         # iterasi kolom dan mengganti nama sesuai mapping
        new_columns = [rename_mapping.get(col, col) for col in df.columns]
        df.columns = new_columns
        try:
            # logging.info(df)
            # try buat convert
            df.to_csv(csv_file, index=False)
            # print kalo sukses buat csvnya
            logging.info(f"CSV saved successfully at {csv_file}")
        except Exception as e:
            logging.error(f"Error saving CSV: {e}")
    else:
        logging.warning("No records were successfully generated. CSV not saved.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate filled PDF forms.")
    parser.add_argument("template", help="Path to the PDF template file.")
    parser.add_argument("output_dir", help="Directory to save the generated PDFs.")
    parser.add_argument("csv_file", help="Path to save the generated CSV file.")
    parser.add_argument("num_records", type=int, help="Number of PDF forms to generate.")

    args = parser.parse_args()
    main(args.template, args.output_dir, args.csv_file, args.num_records)
