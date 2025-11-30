import os
import re
import PyPDF2
import pandas as pd

# -------------------- Folders -------------------- #
PDF_FOLDER = 'uploads'
OUTPUT_FILE = 'output/college_applications.xlsx'

os.makedirs(PDF_FOLDER, exist_ok=True)
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

# -------------------- Field Parsing -------------------- #
def parse_form_text(text):
    """
    Extract all fields from the PDF text using regex.
    Returns a dictionary where keys are column names.
    """
    data = {}

    # Section 1: Personal Information
    data['Full Name'] = re.search(r"Full Name.*?\n(.*)", text).group(1).strip() if re.search(r"Full Name.*?\n(.*)", text) else ""
    data['Date of Birth'] = re.search(r"Date of Birth.*?\n(.*)", text).group(1).strip() if re.search(r"Date of Birth.*?\n(.*)", text) else ""
    data['Age'] = re.search(r"Age.*?\n(.*)", text).group(1).strip() if re.search(r"Age.*?\n(.*)", text) else ""
    data['Gender'] = re.search(r"Gender.*?\n(.*)", text).group(1).strip() if re.search(r"Gender.*?\n(.*)", text) else ""
    data['Nationality'] = re.search(r"Nationality.*?\n(.*)", text).group(1).strip() if re.search(r"Nationality.*?\n(.*)", text) else ""
    data['Country of Origin'] = re.search(r"Country of Origin.*?\n(.*)", text).group(1).strip() if re.search(r"Country of Origin.*?\n(.*)", text) else ""
    data['Country of Residence'] = re.search(r"Country of Residence.*?\n(.*)", text).group(1).strip() if re.search(r"Country of Residence.*?\n(.*)", text) else ""
    data['Category'] = re.search(r"Category.*?\n(.*)", text).group(1).strip() if re.search(r"Category.*?\n(.*)", text) else ""
    data['Caste Certificate No.'] = re.search(r"Caste Certificate No.*?\n(.*)", text).group(1).strip() if re.search(r"Caste Certificate No.*?\n(.*)", text) else ""
    data['Aadhaar / National ID'] = re.search(r"Aadhaar / National ID.*?\n(.*)", text).group(1).strip() if re.search(r"Aadhaar / National ID.*?\n(.*)", text) else ""

    # Section 2: Contact Information
    data['Mobile Number'] = re.search(r"Mobile Number.*?\n(.*)", text).group(1).strip() if re.search(r"Mobile Number.*?\n(.*)", text) else ""
    data['Alternate Mobile Number'] = re.search(r"Alternate Mobile Number.*?\n(.*)", text).group(1).strip() if re.search(r"Alternate Mobile Number.*?\n(.*)", text) else ""
    data['Email Address'] = re.search(r"Email Address.*?\n(.*)", text).group(1).strip() if re.search(r"Email Address.*?\n(.*)", text) else ""
    data['Current Address'] = re.search(r"Current Address.*?\n(.*)", text).group(1).strip() if re.search(r"Current Address.*?\n(.*)", text) else ""
    data['Permanent Address'] = re.search(r"Permanent Address.*?\n(.*)", text).group(1).strip() if re.search(r"Permanent Address.*?\n(.*)", text) else ""
    data['Parent/Guardian Name'] = re.search(r"Parent/Guardian Name.*?\n(.*)", text).group(1).strip() if re.search(r"Parent/Guardian Name.*?\n(.*)", text) else ""
    data['Parent/Guardian Contact'] = re.search(r"Parent/Guardian Contact Number.*?\n(.*)", text).group(1).strip() if re.search(r"Parent/Guardian Contact Number.*?\n(.*)", text) else ""
    data['Parent/Guardian Email'] = re.search(r"Parent/Guardian Email.*?\n(.*)", text).group(1).strip() if re.search(r"Parent/Guardian Email.*?\n(.*)", text) else ""

    # Section 3: Academic Background
    data['Class 10 School'] = re.search(r"Class 10 \(SSC\).*?\n(.*)", text).group(1).strip() if re.search(r"Class 10 \(SSC\).*?\n(.*)", text) else ""
    data['Class 12 School'] = re.search(r"Class 12 \(HSC\).*?\n(.*)", text).group(1).strip() if re.search(r"Class 12 \(HSC\).*?\n(.*)", text) else ""
    data['Bachelor Degree'] = re.search(r"Bachelor’s Degree.*?\n(.*)", text).group(1).strip() if re.search(r"Bachelor’s Degree.*?\n(.*)", text) else ""

    # Section 4: Program Details
    data['Program Applied For'] = re.search(r"Program Applied For.*?\n(.*)", text).group(1).strip() if re.search(r"Program Applied For.*?\n(.*)", text) else ""
    data['Specialization / Major'] = re.search(r"Specialization / Major.*?\n(.*)", text).group(1).strip() if re.search(r"Specialization / Major.*?\n(.*)", text) else ""
    data['Mode of Study'] = re.search(r"Mode of Study.*?\n(.*)", text).group(1).strip() if re.search(r"Mode of Study.*?\n(.*)", text) else ""
    data['Academic Year'] = re.search(r"Academic Year of Admission.*?\n(.*)", text).group(1).strip() if re.search(r"Academic Year of Admission.*?\n(.*)", text) else ""
    data['Preferred Campus'] = re.search(r"Preferred Campus.*?\n(.*)", text).group(1).strip() if re.search(r"Preferred Campus.*?\n(.*)", text) else ""

    # Section 6: Payment Details
    data['Application Fee'] = re.search(r"Application Fee Amount.*?\n(.*)", text).group(1).strip() if re.search(r"Application Fee Amount.*?\n(.*)", text) else ""
    data['Payment Mode'] = re.search(r"Payment Mode.*?\n(.*)", text).group(1).strip() if re.search(r"Payment Mode.*?\n(.*)", text) else ""
    data['Transaction ID / Receipt'] = re.search(r"Transaction ID / Receipt No.*?\n(.*)", text).group(1).strip() if re.search(r"Transaction ID / Receipt No.*?\n(.*)", text) else ""
    data['Date of Payment'] = re.search(r"Date of Payment.*?\n(.*)", text).group(1).strip() if re.search(r"Date of Payment.*?\n(.*)", text) else ""

    return data

# -------------------- Main Workflow -------------------- #
def main():
    pdf_files = [f for f in os.listdir(PDF_FOLDER) if f.lower().endswith('.pdf')]
    if not pdf_files:
        print(f"No PDFs found in {PDF_FOLDER}. Place your Word-exported PDFs there.")
        return

    all_data = []
    for pdf in pdf_files:
        path = os.path.join(PDF_FOLDER, pdf)
        print(f"Processing {pdf}...")
        text = ""
        try:
            with open(path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            print(f"Error reading {pdf}: {e}")
            continue

        form_data = parse_form_text(text)
        form_data['File Name'] = pdf  # optional: track file name
        all_data.append(form_data)

    # Save to Excel
    if all_data:
        df = pd.DataFrame(all_data)
        df.to_excel(OUTPUT_FILE, index=False)
        print(f"✅ Saved {len(all_data)} entries to {OUTPUT_FILE}")
    else:
        print("No data extracted from PDFs.")

if __name__ == "__main__":
    main()
