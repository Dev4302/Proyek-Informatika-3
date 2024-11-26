import os
import pandas as pd
from faker import Faker
from fillpdf import fillpdfs
import argparse
import logging
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Constants
STANDARD_DEDUCTION = 10350
TAX_RATE = 0.1
FORM = 1

fake = Faker()

def random_data():
    return {
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "ssn": fake.ssn(),
        "address": fake.street_address(),
        "city_state_zip": f"{fake.city()}, {fake.state()} {fake.zipcode()}",
        "phone": fake.phone_number(),
        "routing_number": fake.random_number(digits=9),
        "account_number": fake.random_number(digits=12),
        "occupation": fake.job(),
        "wages": fake.random_int(min=1000, max=100000),
        "taxable_interest": fake.random_int(min=0, max=1500),
        "unemployment_comp": fake.random_int(min=0, max=10000),
        "tax_withheld": fake.random_int(min=0, max=10000),
        "eic": fake.random_int(min=0, max=2000),
        "health_care": fake.random_int(min=0, max=1000),
    }

def calculate_fields(data):
    data["gross_income"] = data["wages"] + data["taxable_interest"] + data["unemployment_comp"]
    data["deduction"] = STANDARD_DEDUCTION
    data["taxable_income"] = max(data["gross_income"] - data["deduction"], 0)
    data["tax"] = data["taxable_income"] * TAX_RATE
    data["total_payments"] = data["tax_withheld"] + data["eic"]
    data["total_tax"] = data["tax"] + data["health_care"]
    data["refund"] = max(data["total_payments"] - data["total_tax"], 0)
    data["owed"] = max(data["total_tax"] - data["total_payments"], 0)
    return data

def fill_pdf(template, output, data):
    fields = fillpdfs.get_form_fields(template)
    fillpdfs.write_fillable_pdf(template, output, fields)

def process_record(template, output_dir, record_id):
    try:
        record = random_data()
        record = calculate_fields(record)
        pdf_name = os.path.join(output_dir, f"form_{record_id+1}.pdf")
        fill_pdf(template, pdf_name, record)
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
        except Exception as e:
            logging.error(f"Error saving CSV: {e}")
    else:
        logging.warning("No records were successfully generated. CSV not saved.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fill PDF forms with random data.")
    parser.add_argument("template", help="Path to the PDF form template.")
    parser.add_argument("output_dir", help="Directory to save filled PDF forms.")
    parser.add_argument("csv_file", help="Path to save CSV file.")
    parser.add_argument("--num", type=int, default=FORM, help="Number of forms to generate.")
    args = parser.parse_args()

    main(args.template, args.output_dir, args.csv_file, args.num)
