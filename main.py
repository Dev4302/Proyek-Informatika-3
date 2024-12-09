import os
import logging
import argparse
import re
import pandas as pd
from faker import Faker
from concurrent.futures import ThreadPoolExecutor
from pdfrw import PdfReader, PdfWriter, IndirectPdfDict

# # cli
# # python main.py f1040ez--2016.pdf output_forms filled_data.csv
# # python main.py form.pdf output_forms filled_data.csv

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

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

def random_data_generator(form_fields) :
    # generated field
    rand_data = {
        form_fields[0]: fake.first_name(),
        form_fields[1]: fake.last_name(),
        form_fields[2]: fake.ssn().replace('-', ''),
        form_fields[6]: fake.street_address(),
        form_fields[7]: fake.building_number(),
        form_fields[8]: fake.city() + " " + fake.state()  + " " + fake.zipcode(),
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

    #calculation field
    gross = rand_data[form_fields[14]] + rand_data[form_fields[16]] + rand_data[form_fields[18]]
    taxable_income = max(gross - rand_data[form_fields[24]],0)
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

    rand_data |= cal_field #bind field

    return rand_data

def fill_data(template, output, data):
    template_pdf = PdfReader(template)
    annotations = template_pdf.pages[0]['/Annots']

    # Iterate semua field
    for annotation in annotations:
        if annotation['/Subtype'] == '/Widget' and annotation['/T']:
            field_name = annotation['/T'][1:-1]  #ambil nama field (remove parentheses)
            cleaned_field_name = clean_field_name(field_name)  # Clean the field name

            # Check nama field ada di data fill/ data_dict
            if cleaned_field_name in data:
                annotation.update(
                    IndirectPdfDict(V='{}'.format(data[cleaned_field_name]))  # isi field
                )

    # Save the filled PDF
    PdfWriter(output, trailer=template_pdf).write()

def process_record(template, output_dir, record_id):
    try:
        record = random_data_generator(get_field(template))
        pdf_name = os.path.join(output_dir, f"form_{record_id+1}.pdf")
        fill_data(template, pdf_name, record)
        logging.info(f"PDF generated: {pdf_name}")
        return record
    except Exception as e:
        logging.error(f"Error processing record {record_id+1}: {e}")
        return None

def main(template, output_dir, csv_file, num_records):
    # Validate inputs
    if not os.path.isfile(template):
        raise FileNotFoundError(f"Template file not found: {template}")
    if not os.access(os.path.dirname(output_dir) or ".", os.W_OK):
        raise PermissionError(f"No write access to directory: {output_dir}")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    logging.info("Starting record generation...")
    with ThreadPoolExecutor() as executor:
        results = list(executor.map(
            lambda i: process_record(template, output_dir, i),
            range(num_records)
        ))

    # Filter out failed records
    csv_data = [record for record in results if record]

    # Save to CSV
    if csv_data:
        df = pd.DataFrame(csv_data)
        try:
            df.to_csv(csv_file, index=False)
            logging.info(f"CSV saved successfully at {csv_file}")
            rename_csv()
        except Exception as e:
            logging.error(f"Error saving CSV: {e}")
    else:
        logging.warning("No records were successfully generated. CSV not saved.")

def rename_csv():
    column_mapping = {
        "f1_1[0]": "firstname",
        "f1_2[0]": "lastname",
        "f1_3[0]": "ssn",
        "f1_6[0]": "adress",
        "f1_7[0]": "apt no",
        "f1_8[0]": "adress2",
        "f1_12[0]": "wages",
        "f1_14[0]": "interest",
        "f1_16[0]": "un-comp",
        "f1_18[0]": "gross",
        "c1_3[0]": "Off",
        "c1_4[0]": "Off",
        "f1_20[0]": "deduction",
        "f1_22[0]": "taxable-income",
        "f1_24[0]": "withheld",
        "f1_26[0]": "eic",
        "f1_30[0]": "total-payment",
        "f1_32[0]": "tax",
        "c1_05[0]": "Off",
        "f1_34[0]": "health-care",
        "f1_36[0]": "total-tax",
        "c1_6[0]": "Off",
        "f1_38[0]": "refund",
        "f1_40[0]": "routing",
        "f1_41[0]": "acc-num",
        "f1_42[0]": "owed",
        "f1_47[0]": "occupation",
        "f1_48[0]": "phone",
    }

    csv_file = "filled_data.csv"
    output_file = "data.csv" 

    # Read the CSV
    df = pd.read_csv(csv_file)

    # Rename the columns
    df.rename(columns=column_mapping, inplace=True)

    # Save the updated CSV
    df.to_csv(output_file, index=False)

    os.remove(csv_file)

    print(f"CSV columns renamed and saved to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fill PDF forms with random data.")
    parser.add_argument("template", help="Path to the PDF form template.")
    parser.add_argument("output_dir", help="Directory to save filled PDF forms.")
    parser.add_argument("csv_file", help="Path to save CSV file.")
    parser.add_argument("--num", type=int, default=FORM, help="Number of forms to generate.")
    args = parser.parse_args()

    main(args.template, args.output_dir, args.csv_file, args.num)
