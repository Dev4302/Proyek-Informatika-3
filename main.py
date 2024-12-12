import os
import logging
import re
from tkinter import font
import pandas as pd
from faker import Faker
from concurrent.futures import ThreadPoolExecutor
from pdfrw import PdfReader, PdfWriter, IndirectPdfDict
import tkinter as tk
from tkinter import filedialog, messagebox

# logging 
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# parameter static
SINGLE_DEDUCTION = 10350
DOUBLE_DEDUCTION = 20700
TAX_RATE = 0.1
FORM = 1

# inisialisasi faker untuk generate data sintetis
fake = Faker()

# funtion untuk membersihkan field PDF dari BOM
def clean_field_name(field_name):
    try:
        cleaned_name = field_name.encode('latin1').decode('utf-16')
    except UnicodeDecodeError:
        cleaned_name = field_name.encode('latin1').decode('utf-8', 'ignore')

    cleaned_name = re.sub(r'[^\w\s]', '', cleaned_name)
    
    return cleaned_name.strip()

# funtion untuk mengambil field PDF
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

# function untuk mengenerate data sintetis
def random_data_generator(form_fields):
    # field yang dapat lansung di-generate
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

    # Spesifikasi rentang nilai

    # Numerical values in the form should be random values within ranges below, 
    # but calculated numerical fields should still be populated based on instructions in the form 
    #  (straightforward calculations, add or deduct a couple of values). 
    #     Ranges:
    #     Wages - [1000 - 100.000]
    #     Taxable interest - [0 - 1500]
    #     Unemployment compensation - [0 - 10000]
    #     Tax withheld - [0-10.000]
    #     EIC - [0-2.000]
    #     Health care - [0-1.000]
    #     Calculate tax for line #10 as 10% of line 6

    # perhitungan berdasarkan spesifikasi
    gross = rand_data[form_fields[14]] + rand_data[form_fields[16]] + rand_data[form_fields[18]]
    taxable_income = max(gross - rand_data[form_fields[24]], 0)
    total_payment = rand_data[form_fields[28]] + rand_data[form_fields[30]]
    tax = taxable_income * TAX_RATE
    total_tax = tax + rand_data[form_fields[39]]
    refund = max(total_payment - total_tax, 0)
    owed = max(total_tax - total_payment, 0)

    # field yang perlu dihitung terlebih dahulu
    cal_field = {
        form_fields[20]: gross,
        form_fields[26]: taxable_income,
        form_fields[34]: total_payment,
        form_fields[36]: tax,
        form_fields[41]: total_tax,
        form_fields[44]: refund,
        form_fields[50]: owed
    }

    # bind kedua field
    rand_data |= cal_field
    # keluaran berupa dict yang bersisi field-field yang perlu digenerate
    return rand_data

# function untuk mengisi data ke PDF
def fill_data(template, output, data):
    template_pdf = PdfReader(template)
    annotations = template_pdf.pages[0]['/Annots']

    # Iterate semua field
    for annotation in annotations:
        if annotation['/Subtype'] == '/Widget' and annotation['/T']:
            field_name = annotation['/T'][1:-1]
            cleaned_field_name = clean_field_name(field_name)

            # Check nama field ada di data fill/ data_dict
            if cleaned_field_name in data:
                annotation.update(
                    IndirectPdfDict(V='{}'.format(data[cleaned_field_name]))
                )

    # Save PDF yang sudah terisi
    PdfWriter(output, trailer=template_pdf).write()

# funtion untuk memproses PDF
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
    
#function utama
def main(template, output_dir, csv_file, num_records):
    # validasi inputs
    if not os.path.isfile(template):
        raise FileNotFoundError(f"Template file not found: {template}")
    if not os.access(os.path.dirname(output_dir) or ".", os.W_OK):
        raise PermissionError(f"No write access to directory: {output_dir}")
    
    # membuat directory output baru jika belum ada
    os.makedirs(output_dir, exist_ok=True)

    logging.info("Starting record generation...")

    # ini eksekusi buat multithreading bikin pdfnya
    with ThreadPoolExecutor() as executor:
        results = list(executor.map(
            lambda i: process_record(template, output_dir, i),
            range(num_records)
        ))

    # filter data invalid
    csv_data = [record for record in results if record]

    # buat csv
    if csv_data:
        df = pd.DataFrame(csv_data)
        # sebelum diconvert ke csv, tambahin dulu nama kolom nama file disini
        df.insert(0, 'File_name', [f'form_{i}.pdf' for i in range(len(df))])
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
        except Exception as e:
            logging.error(f"Error saving CSV: {e}")
    else:
        logging.warning("No records were successfully generated. CSV not saved.")

# Aspek UI
def pilih_template():
    file_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
    if file_path:
        template_label.config(text=f"Template: {file_path}")
        global template_path
        template_path = file_path
    else:
        template_label.config(text="No template selected")

def pilih_output_dir():
    directory = filedialog.askdirectory()
    if directory:
        output_label.config(text=f"Output Dir: {directory}")
        global output_dir
        output_dir = directory
    else:
        output_label.config(text="No output directory selected")
        
def mulai_proses():
    if not template_path or not output_dir:
        messagebox.showerror("Error", "Template dan Output Directory harus dipilih!")
        return
    
    # Otomatisasi CSV Path
    csv_file = os.path.join(output_dir, "filled_data.csv")  
    try:
        main(template_path, output_dir, csv_file, int(num_entry.get()))
        messagebox.showinfo("Sukses", f"Proses selesai! CSV disimpan di {csv_file}")
    except Exception as e:
        messagebox.showerror("Error", f"Terjadi kesalahan: {e}")

root = tk.Tk()
root.title("PDF Form Filler")
width = int(root.winfo_screenwidth() * 0.3)
height = int(root.winfo_screenheight() * 0.35)
root.geometry(f"{width}x{height}")

template_label = tk.Label(root, text="No template selected", wraplength=400)
template_label.pack(pady=5)

pilih_template_button = tk.Button(root, text="Pilih Template", command=pilih_template)
pilih_template_button.pack(pady=5)

output_label = tk.Label(root, text="No output directory selected", wraplength=400)
output_label.pack(pady=5)

pilih_output_button = tk.Button(root, text="Pilih Output Directory", command=pilih_output_dir)
pilih_output_button.pack(pady=5)

num_label = tk.Label(root, text="Jumlah PDF:")
num_label.pack(pady=5)

num_entry = tk.Entry(root, width=10)
num_entry.insert(0, "1")
num_entry.pack(pady=5)

mulai_button = tk.Button(root, text="Generate", command=mulai_proses)
mulai_button.pack(pady=10)

global_font = font.nametofont("TkDefaultFont")
global_font.config(family="lato", size=12)
root.option_add("*Font", global_font)
root.mainloop()