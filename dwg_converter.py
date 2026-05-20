#!/usr/bin/env python3
"""
DWG to Geodatabase/GeoPackage Converter
Converts DWG files with annotations, multipatch, points, polygons, polylines, and text to GDB or GPKG
"""

import os
import sys
from osgeo import ogr, gdal

# Enable GDAL exceptions
gdal.UseExceptions()

def convert_dwg_to_geo(input_dwg, output_path, output_format='GPKG'):
    """
    Convert DWG file to Geodatabase or GeoPackage
    
    Parameters:
    -----------
    input_dwg : str
        Path to input DWG file
    output_path : str
        Path to output file/directory
    output_format : str
        'GPKG' for GeoPackage or 'OpenFileGDB' for File Geodatabase
    """
    
    # Validate input file
    if not os.path.exists(input_dwg):
        raise FileNotFoundError(f"Input DWG file not found: {input_dwg}")
    
    print(f"Opening DWG file: {input_dwg}")
    
    # Open DWG file
    dwg_ds = ogr.Open(input_dwg, 0)  # 0 = read-only
    if dwg_ds is None:
        raise Exception(f"Failed to open DWG file. Make sure GDAL has DWG support compiled.")
    
    print(f"DWG file opened successfully. Found {dwg_ds.GetLayerCount()} layers.")
    
    # Create output driver
    if output_format == 'GPKG':
        driver = ogr.GetDriverByName('GPKG')
        if os.path.exists(output_path):
            os.remove(output_path)
        output_ds = driver.CreateDataSource(output_path)
        print(f"Creating GeoPackage: {output_path}")
    elif output_format == 'OpenFileGDB':
        driver = ogr.GetDriverByName('OpenFileGDB')
        if os.path.exists(output_path):
            driver.DeleteDataSource(output_path)
        output_ds = driver.CreateDataSource(output_path)
        print(f"Creating File Geodatabase: {output_path}")
    else:
        raise ValueError("output_format must be 'GPKG' or 'OpenFileGDB'")
    
    if output_ds is None:
        raise Exception(f"Failed to create output {output_format}")
    
    # Process each layer in the DWG
    layer_count = dwg_ds.GetLayerCount()
    converted_layers = 0
    
    for i in range(layer_count):
        source_layer = dwg_ds.GetLayerByIndex(i)
        layer_name = source_layer.GetName()
        feature_count = source_layer.GetFeatureCount()
        
        print(f"\nProcessing layer {i+1}/{layer_count}: {layer_name} ({feature_count} features)")
        
        if feature_count == 0:
            print(f"  Skipping empty layer: {layer_name}")
            continue
        
        # Get layer geometry type
        geom_type = source_layer.GetGeomType()
        geom_type_name = ogr.GeometryTypeToName(geom_type)
        print(f"  Geometry type: {geom_type_name}")
        
        # Get spatial reference
        srs = source_layer.GetSpatialRef()
        
        # Sanitize layer name for output (remove special characters)
        clean_layer_name = layer_name.replace(':', '_').replace(' ', '_')
        
        # Create output layer
        try:
            output_layer = output_ds.CreateLayer(
                clean_layer_name, 
                srs=srs, 
                geom_type=geom_type
            )
        except Exception as e:
            print(f"  Warning: Could not create layer {clean_layer_name}: {e}")
            continue
        
        # Copy field definitions
        source_layer_defn = source_layer.GetLayerDefn()
        for j in range(source_layer_defn.GetFieldCount()):
            field_defn = source_layer_defn.GetFieldDefn(j)
            output_layer.CreateField(field_defn)
        
        # Copy features
        output_layer_defn = output_layer.GetLayerDefn()
        features_copied = 0
        
        source_layer.ResetReading()
        for source_feature in source_layer:
            # Create new feature
            output_feature = ogr.Feature(output_layer_defn)
            
            # Copy geometry
            geom = source_feature.GetGeometryRef()
            if geom is not None:
                output_feature.SetGeometry(geom.Clone())
            
            # Copy attributes
            for j in range(source_layer_defn.GetFieldCount()):
                field_value = source_feature.GetField(j)
                output_feature.SetField(j, field_value)
            
            # Add feature to output layer
            output_layer.CreateFeature(output_feature)
            features_copied += 1
            
            # Clean up
            output_feature = None
        
        print(f"  Copied {features_copied} features")
        converted_layers += 1
    
    # Clean up
    dwg_ds = None
    output_ds = None
    
    print(f"\n{'='*60}")
    print(f"Conversion complete!")
    print(f"Converted {converted_layers} layers from DWG to {output_format}")
    print(f"Output saved to: {output_path}")
    print(f"{'='*60}")

def list_dwg_layers(input_dwg):
    """
    List all layers in a DWG file with their properties
    """
    dwg_ds = ogr.Open(input_dwg, 0)
    if dwg_ds is None:
        raise Exception(f"Failed to open DWG file: {input_dwg}")
    
    print(f"\nDWG File: {input_dwg}")
    print(f"{'='*80}")
    print(f"Total layers: {dwg_ds.GetLayerCount()}\n")
    
    for i in range(dwg_ds.GetLayerCount()):
        layer = dwg_ds.GetLayerByIndex(i)
        print(f"Layer {i+1}: {layer.GetName()}")
        print(f"  Geometry Type: {ogr.GeometryTypeToName(layer.GetGeomType())}")
        print(f"  Feature Count: {layer.GetFeatureCount()}")
        print(f"  Spatial Reference: {layer.GetSpatialRef()}")
        
        # Show field names
        layer_defn = layer.GetLayerDefn()
        if layer_defn.GetFieldCount() > 0:
            print(f"  Fields: {', '.join([layer_defn.GetFieldDefn(j).GetName() for j in range(layer_defn.GetFieldCount())])}")
        print()
    
    dwg_ds = None

def main():
    """
    Main function with command-line interface
    """
    if len(sys.argv) < 2:
        print("DWG to Geodatabase/GeoPackage Converter")
        print("\nUsage:")
        print("  List layers:    python dwg_converter.py <input.dwg> --list")
        print("  To GeoPackage:  python dwg_converter.py <input.dwg> <output.gpkg>")
        print("  To Geodatabase: python dwg_converter.py <input.dwg> <output.gdb> --gdb")
        print("\nExamples:")
        print("  python dwg_converter.py myfile.dwg --list")
        print("  python dwg_converter.py myfile.dwg output.gpkg")
        print("  python dwg_converter.py myfile.dwg output.gdb --gdb")
        sys.exit(1)
    
    input_dwg = sys.argv[1]
    
    # List layers only
    if len(sys.argv) == 3 and sys.argv[2] == '--list':
        list_dwg_layers(input_dwg)
        return
    
    # Convert
    if len(sys.argv) < 3:
        print("Error: Output path required")
        sys.exit(1)
    
    output_path = sys.argv[2]
    
    # Determine output format
    if len(sys.argv) >= 4 and sys.argv[3] == '--gdb':
        output_format = 'OpenFileGDB'
        if not output_path.endswith('.gdb'):
            output_path += '.gdb'
    else:
        output_format = 'GPKG'
        if not output_path.endswith('.gpkg'):
            output_path += '.gpkg'
    
    try:
        convert_dwg_to_geo(input_dwg, output_path, output_format)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
