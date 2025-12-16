# -*- coding: utf-8 -*-
"""
Created on Wed Oct 15 16:33:39 2025

@author: parvesh.reddy_crmit
"""
import fcsparser
import pandas as pd
import re

# Function to clean metadata (keys and values)
def clean_metadata(metadata):
    cleaned_metadata = {}

    # Excel invalid characters list (CSV doesn't require this, but let's keep it for consistency)
    invalid_characters = r'[\\/*?:"<>|]'

    for key, value in metadata.items():
        # Clean the key: Remove problematic characters and sequences
        cleaned_key = key.replace('$', '').replace(' ', '_').replace('\n', '_').replace('\r', '').strip()

        # Ensure the key doesn't contain any other unsupported characters
        cleaned_key = re.sub(invalid_characters, '_', cleaned_key)

        # Ensure the key is not too long (Excel has a limit of 31 characters for sheet names/columns)
        if len(cleaned_key) > 31:
            cleaned_key = cleaned_key[:31]

        # Sanitize the value: Replace newline, carriage return, and handle non-strings
        if isinstance(value, str):
            cleaned_value = value.replace('\n', ' ').replace('\r', '').strip()
        else:
            cleaned_value = str(value)  # Convert non-strings to string

        # Handle NaN or None values
        if cleaned_value == "nan" or cleaned_value.lower() == "none":
            cleaned_value = "Not Available"

        # Add the cleaned data
        cleaned_metadata[cleaned_key] = cleaned_value
    
    return cleaned_metadata

# Function to sanitize the column names in the data to make them CSV compatible
def sanitize_column_names(columns):
    sanitized_columns = []
    invalid_characters = r'[\\/*?:"<>|]'

    for col in columns:
        # Remove spaces, special characters, and replace with underscores
        sanitized_col = col.replace(' ', '_').replace('\n', '_').replace('\r', '').strip()
        
        # Remove any invalid characters for CSV
        sanitized_col = re.sub(invalid_characters, '_', sanitized_col)

        # Ensure the column name is not too long (Excel limit is 31 characters, but we can be generous in CSV)
        if len(sanitized_col) > 100:
            sanitized_col = sanitized_col[:100]

        sanitized_columns.append(sanitized_col)
    
    return sanitized_columns

# Function to extract metadata and data from FCS file and save it to CSV file
def fcs_to_csv(fcs_file_path, metadata_output_file, data_output_file):
    try:
        # Parse the FCS file to get metadata and data
        metadata, data = fcsparser.parse(fcs_file_path)

        # Clean the metadata
        cleaned_metadata = clean_metadata(metadata)

        # Convert the cleaned metadata dictionary into a DataFrame
        metadata_df = pd.DataFrame(list(cleaned_metadata.items()), columns=['Metadata Key', 'Value'])  # type: ignore[call-overload]

        # Clean the column names for the data to be CSV compatible
        sanitized_columns = sanitize_column_names(data.columns)

        # Convert the data into a DataFrame and apply the sanitized column names
        data_df = pd.DataFrame(data)
        data_df.columns = sanitized_columns

        # Save metadata and data to CSV files
        metadata_df.to_csv(metadata_output_file, index=False)
        data_df.to_csv(data_output_file, index=False)

        print(f"FCS file has been successfully converted to CSV. Metadata saved to {metadata_output_file}, Data saved to {data_output_file}")
    
    except Exception as e:
        print(f"An error occurred while processing the FCS file: {e}")


# Replace with your FCS file path and desired output Excel file path
fcs_file_path = r'C:\Users\parvesh.reddy_crmit\Downloads\0.25ug ISO SEC.fcs'  # Replace with the path to your FCS file
metadata_output_file = r'C:\Users\parvesh.reddy_crmit\Downloads\metatest.csv'
data_output_file = r'C:\Users\parvesh.reddy_crmit\Downloads\test.csv'  # Output Excel file name

# Extract metadata and save to Excel
fcs_to_csv(fcs_file_path, metadata_output_file, data_output_file)

