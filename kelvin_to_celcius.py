import os
import rasterio
import numpy as np

# Define input and output folders
input_folder = r"C:\Users\91956\Downloads\UTCI_Heatstress\UTCI_Clipped\2015"
output_folder = r"C:\Users\91956\Downloads\UTCI_Heatstress\UTCI_Celsius_2015"

# Ensure the output folder exists
os.makedirs(output_folder, exist_ok=True)

# Function to convert Kelvin to Celsius and save the new raster
def convert_kelvin_to_celsius(input_path, output_path):
    with rasterio.open(input_path) as src:
        # Copy metadata and update it for the output file
        metadata = src.meta.copy()
        
        # Iterate through each band
        data = []
        for band_id in range(1, src.count + 1):
            band_data = src.read(band_id)
            nodata_value = src.nodatavals[band_id - 1]
            
            # Mask NoData values
            band_data = np.ma.masked_equal(band_data, nodata_value)
            
            # Convert Kelvin to Celsius
            celsius_data = band_data - 273.15
            
            # Restore NoData values
            celsius_data = np.where(band_data.mask, nodata_value, celsius_data)
            
            data.append(celsius_data)
        
        # Save the new raster with converted data
        with rasterio.open(output_path, 'w', **metadata) as dst:
            for band_id, band_data in enumerate(data, start=1):
                dst.write_band(band_id, band_data.astype(metadata['dtype']))

# Process all TIFF files in the folder
for file_name in os.listdir(input_folder):
    if file_name.endswith('.tif'):
        input_path = os.path.join(input_folder, file_name)
        output_path = os.path.join(output_folder, file_name)
        print(f"Processing {file_name}...")
        convert_kelvin_to_celsius(input_path, output_path)

print("Conversion completed. Files saved in:", output_folder)
