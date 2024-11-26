import os
import logging
import argparse
import pandas as pd
from faker import Faker
from fillpdf import fillpdfs
from concurrent.futures import ThreadPoolExecutor

# # check field
# form_field = fillpdfs.get_form_fields("filled.pdf")

# # for key, value in form_field.items():

# #     form_field.update({key: random.randint(3, 9)})

# for key, value in form_field.items():
#     if value == "":
#         pass
#     else: 
#         print(key + "->" + str(value))

# # cli
# # python main.py f1040ez--2016.pdf output_forms filled_data.csv


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

SINGLE_DEDUCTION = 10350
DOUBLE_DEDUCTION = 20700
TAX_RATE = 0.1
FORM = 1

fake = Faker()

def random_data_generator() :
    # generated field
    form_field = {
        "þÿf1_1[0]": fake.first_name(),
        "þÿf1_2[0]": fake.last_name(),
        "þÿf1_3[0]": fake.ssn(),
        "þÿf1_6[0]": fake.street_address(),
        "þÿf1_7[0]": fake.building_number(),
        "þÿf1_8[0]": fake.city() + " " + fake.state()  + " " + fake.zipcode(),
        "þÿf1_12[0]": fake.random_int(min=1000, max=100000),
        "þÿf1_14[0]": fake.random_int(min=0, max=1500),
        "þÿf1_16[0]": fake.random_int(min=0, max=10000),
        "þÿf1_20[0]": SINGLE_DEDUCTION,
        "þÿf1_24[0]": fake.random_int(min=0, max=10000),
        "þÿf1_26[0]": fake.random_int(min=0, max=2000),
        "þÿf1_34[0]": fake.random_int(min=0, max=1000),
        "þÿf1_40[0]": fake.random_number(digits=9),
        "þÿf1_41[0]": fake.random_number(digits=12),
        "þÿf1_47[0]": fake.job(),
        "þÿf1_48[0]": fake.phone_number(),
    }

    #calculation field
    gross = form_field["þÿf1_12[0]"] + form_field["þÿf1_14[0]"] + form_field["þÿf1_16[0]"]
    taxable_income = max(gross - form_field["þÿf1_20[0]"],0)
    total_payment = form_field["þÿf1_24[0]"] + form_field["þÿf1_26[0]"]
    tax = taxable_income * TAX_RATE
    total_tax = tax + form_field["þÿf1_34[0]"]
    refund = max(total_payment - total_tax, 0)
    owed = max(total_tax - total_payment, 0)

    cal_field = {
        "þÿf1_18[0]": gross,
        "þÿf1_22[0]": taxable_income,
        "þÿf1_30[0]": total_payment,
        "þÿf1_32[0]": tax,
        "þÿf1_36[0]": total_tax,
        "þÿf1_38[0]": refund,
        "þÿf1_42[0]": owed
    }

    form_field |= cal_field #bind field

    return form_field

def fill_data(template, output, data):
    fields = fillpdfs.get_form_fields(template)
    fillpdfs.write_fillable_pdf(template, output, fields)

def process_record(template, output_dir, record_id):
    try:
        record = random_data_generator()
        print(record)
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
        "þÿf1_1[0]": "firstname",
        "þÿf1_2[0]": "lastname",
        "þÿf1_3[0]": "ssn",
        "þÿf1_6[0]": "adress",
        "þÿf1_7[0]": "apt no",
        "þÿf1_8[0]": "adress2",
        "þÿf1_12[0]": "wages",
        "þÿf1_14[0]": "interest",
        "þÿf1_16[0]": "un-comp",
        "þÿf1_18[0]": "gross",
        "þÿc1_3[0]": "Off",
        "þÿc1_4[0]": "Off",
        "þÿf1_20[0]": "deduction",
        "þÿf1_22[0]": "taxable-income",
        "þÿf1_24[0]": "withheld",
        "þÿf1_26[0]": "eic",
        "þÿf1_30[0]": "total-payment",
        "þÿf1_32[0]": "tax",
        "þÿc1_05[0]": "Off",
        "þÿf1_34[0]": "health-care",
        "þÿf1_36[0]": "total-tax",
        "þÿc1_6[0]": "Off",
        "þÿf1_38[0]": "refund",
        "þÿf1_40[0]": "routing",
        "þÿf1_41[0]": "acc-num",
        "þÿf1_42[0]": "owed",
        "þÿf1_47[0]": "occupation",
        "þÿf1_48[0]": "phone",
    }

    csv_file = "filled_data.csv"
    output_file = "data.csv" 

    # Read the CSV
    df = pd.read_csv(csv_file)

    # Rename the columns
    df.rename(columns=column_mapping, inplace=True)

    # Save the updated CSV
    df.to_csv(output_file, index=False)

    print(f"CSV columns renamed and saved to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fill PDF forms with random data.")
    parser.add_argument("template", help="Path to the PDF form template.")
    parser.add_argument("output_dir", help="Directory to save filled PDF forms.")
    parser.add_argument("csv_file", help="Path to save CSV file.")
    parser.add_argument("--num", type=int, default=FORM, help="Number of forms to generate.")
    args = parser.parse_args()

    main(args.template, args.output_dir, args.csv_file, args.num)
