# -*- coding: utf-8 -*-
"""
Created on Thu Nov 14 14:36:24 2024

@author: dengjiahao
"""

import re
import pdfplumber
import pandas as pd

# Function to determine if the table should be extracted based on the header text
def is_relevant_table(text):
    keywords = ['birth', 'infant death', 'abortion', 'termination of birth']
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in keywords)

# Function to process extracted text and convert it into a DataFrame
def process_extracted_table_to_dataframe(text):
    # Split the text into lines
    lines = text.strip().split('\n')
    
    # Extract table number and title
    table_number_match = re.match(r'^Table (\d+)', lines[0])
    if not table_number_match:
        raise ValueError("Text does not start with 'Table' followed by a number")
    table_number = table_number_match.group(1)
    
    # Extract table title from the remaining part of the first line
    table_title = lines[0][len(table_number_match.group(0)):].strip()
    
    # Extract column names from the subsequent line
    column_names = lines[1].split()
    
    # Extract data from the remaining lines
    data = []
    for line in lines[2:]:
        row = line.split()
        if len(row) == len(column_names):
            data.append(row)
        else:
            # Handle cases where data rows may be split across multiple lines
            if data:
                data[-1].extend(row)
            else:
                data.append(row)
    
    # Create a DataFrame from the extracted data
    df = pd.DataFrame(data, columns=column_names)
    
    return df, table_number, table_title

results=[]
# Open the PDF file using pdfplumber
try:
    with pdfplumber.open('vital_stats_2014.pdf') as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            results.append(text)
            if text:
                # Check if the page text starts with "Table" followed by a number and contains relevant information
                if re.match(r'^[Tt]able \d+[A-Z]?', text.strip()):
                    # Save the page text to a file
                    with open(f'data/extracted_filtered_table_{i}.txt', 'w') as file:
                        file.write(text)

    "Text files have been successfully saved based on the updated filtering criteria."

except Exception as e:
    str(e)


df, table_number, table_title = process_extracted_table_to_dataframe(text)
