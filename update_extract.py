import re
import pandas as pd
import pdfplumber
import os

# Function to deduce the year from the PDF file name
def deduce_year_from_filename(filename):
    match = re.search(r'_(\d{4})\b', filename)
    if match:
        return int(match.group(1))
    else:
        raise ValueError("Year not found in the filename")

# Function to process extracted text and extract relevant data
def extract_data_from_pdf(text, year):
    # Split the text into lines
    lines = text.strip().split('\n')
    
    # Extract table number
    table_number_match = re.match(r'^(?i)table (\d+[A-Z]?)', lines[0])
    if not table_number_match:
        raise ValueError("Text does not start with 'Table' followed by a number")
    table_number = table_number_match.group(1)
    
    # Extract table title and year
    title_lines = []
    year_pattern = re.compile(r'(\d{4})')
    found_year = False
    for line in lines[1:]:
        title_lines.append(line.strip())
        if year_pattern.search(line):
            found_year = True
            break
    table_title = ' '.join(title_lines).strip()

    # Extract year from the title lines if it's not already provided
    if not found_year:
        for line in title_lines:
            if year_pattern.search(line):
                found_year = True
                break
    if not found_year:
        raise ValueError("Year not found in the table title or the subsequent line")
    
    # Extract the column names (between title and content lines)
    content_start_idx = len(title_lines) + 1
    column_lines = []
    while content_start_idx < len(lines) and len(re.findall(r'\d+', lines[content_start_idx])) < 2:
        column_lines.append(lines[content_start_idx].strip())
        content_start_idx += 1
    column_names = ' '.join(column_lines).strip()
    
    # Extract the content lines (must contain at least two numeric values)
    content_lines = []
    content_started = False
    for line in lines[content_start_idx:]:
        if len(re.findall(r'\d+', line)) >= 2:
            content_started = True
        if content_started:
            content_lines.append(line)
    
    if not content_lines:
        raise ValueError("Could not find content with at least two numeric values")
    
    # Process each content line to merge items based on given rules
    processed_data = []
    skip_next_line = False
    for idx, line in enumerate(content_lines):
        if skip_next_line:
            skip_next_line = False
            continue

        items = line.split()
        row = []
        skip_next = False
        i = 0
        while i < len(items):
            if skip_next:
                skip_next = False
                i += 1
                continue

            # Rule 1: Merge items starting with 'population' and ending with '*' or '-'
            if items[i].lower().startswith('population'):
                merged_item = items[i]
                while i + 1 < len(items) and (items[i + 1].endswith('*') or items[i + 1] == '-'):
                    i += 1
                    merged_item += ' ' + items[i]
                row.append(merged_item)
            
            # Rule 2: Merge consecutive non-numeric values (except if all are '-')
            elif not re.match(r'^-?\d+[.,]?\d*$', items[i]):
                merged_item = items[i]
                while i + 1 < len(items) and not re.match(r'^-?\d+[.,]?\d*$', items[i + 1]) and items[i + 1] != '-':
                    i += 1
                    merged_item += ' ' + items[i]
                row.append(merged_item)
            
            # Rule 3: Merge items with '-' between two numeric values
            elif i + 2 < len(items) and re.match(r'^\d+[.,]?\d*$', items[i]) and items[i + 1] == '-' and re.match(r'^\d+[.,]?\d*$', items[i + 2]):
                merged_item = f"{items[i]} {items[i + 1]} {items[i + 2]}"
                row.append(merged_item)
                skip_next = True  # Skip the next two items as they are already merged
                i += 2
            
            # Rule 4: Merge specific phrases like 'Under 16' or '45 and Over'
            elif items[i].lower() == 'under' and i + 1 < len(items) and items[i + 1] == '16':
                row.append(f"{items[i]} {items[i + 1]}")
                skip_next = True
            elif items[i] == '45' and i + 2 < len(items) and items[i + 1].lower() == 'and' and items[i + 2].lower() == 'over':
                row.append(f"{items[i]} {items[i + 1]} {items[i + 2]}")
                skip_next = True
                i += 2
            
            # Rule 7: Merge consecutive cells that start with an English letter and contain '<' or '>' until a number appears
            elif re.match(r'^[a-zA-Z]', items[i]) and ('<' in items[i] or '>' in items[i]):
                merged_item = items[i]
                while i + 1 < len(items) and not re.match(r'^\d+[.,]?\d*$', items[i + 1]):
                    i += 1
                    merged_item += ' ' + items[i]
                row.append(merged_item)
            
            else:
                # Keep the item as is
                row.append(items[i])
            i += 1

        # Rule 5: Merge specific long phrases that span multiple lines
        if idx + 1 < len(content_lines):
            next_line = content_lines[idx + 1].strip()
            if (line.strip() == "Benign Neoplasms, Carcinoma In Situ, and Neoplasms of" and
                next_line == "Uncertain Behavior and of Unspecified Nature"):
                row = [line.strip() + ' ' + next_line]
                skip_next_line = True
            elif (line.strip() == "Acute and Rapidly Progressive Nephritic and" and
                  next_line == "Nephrotic Syndrome"):
                row = [line.strip() + ' ' + next_line]
                skip_next_line = True
            elif (line.strip() == "Chronic Glomerulonephritis, Nephritis and Nephritis not" and
                  next_line == "Specified as Acute or Chronic & Renal Sclerosis Unspecifei d"):
                row = [line.strip() + ' ' + next_line]
                skip_next_line = True

        # Rule 6: Delete lines containing "List of 67 Selected Causes of Death"
        if "List of 67 Selected Causes of Death" in line:
            continue

        processed_data.append(row)
    
    return processed_data, table_number, table_title, column_names

# Extract and save tables from all PDF files in the folder
try:
    pdf_folder = 'pdf files'
    output_directory = 'data'

    # Traverse all files in the PDF folder
    for pdf_filename in os.listdir(pdf_folder):
        if pdf_filename.endswith('.pdf'):
            try:
                year = deduce_year_from_filename(pdf_filename)
                year_directory = os.path.join(output_directory, str(year))

                # Create the year directory if it doesn't exist
                if not os.path.exists(year_directory):
                    os.makedirs(year_directory)
                
                table_count = {}
                
                pdf_path = os.path.join(pdf_folder, pdf_filename)
                with pdfplumber.open(pdf_path) as pdf:
                    for i, page in enumerate(pdf.pages):
                        text = page.extract_text()
                        if text:
                            # Check if the page text starts with "Table", "TABLE", or "table" followed by a number
                            if re.match(r'^(?i)table \d+[A-Z]?', text.strip()):
                                try:
                                    #print(year,True)
                                    # Extract data from the PDF page
                                    processed_data, table_number, table_title, column_names = extract_data_from_pdf(text, year)
                                    
                                    # Sanitize the table title for the filename
                                    sanitized_title = re.sub(r'[^A-Za-z0-9_]+', '_', table_title)
                                    
                                    # Determine the filename and handle multiple tables with the same number
                                    if table_number not in table_count:
                                        table_count[table_number] = 1
                                    else:
                                        table_count[table_number] += 1
                                    
                                    # Create a DataFrame from the processed data
                                    data = [[f'Table {table_number}']]  # Add table number
                                    data.append([table_title])  # Add table title
                                    data.append([column_names])  # Add column names
                                    data.extend(processed_data)  # Add processed data
                                    df = pd.DataFrame(data)
                                    
                                    # Save the DataFrame to an Excel file
                                    if table_count[table_number] == 1:
                                        excel_filename = os.path.join(year_directory, f"Table_{table_number}.xlsx")
                                    else:
                                        excel_filename = os.path.join(year_directory, f"Table_{table_number}_{table_count[table_number]}.xlsx")
                                    df.to_excel(excel_filename, index=False, header=False)
                                    print(f"Successfully saved: {excel_filename}")
                                except Exception as e:
                                    print(f"Error processing table on page {i + 1} of {pdf_filename}: {str(e)}")
            except Exception as e:
                print(f"Error processing file {pdf_filename}: {str(e)}")

    print("Tables have been successfully extracted and saved.")

except Exception as e:
    print(str(e))