#!/usr/bin/env python3
"""
DWG/DXF to Geodatabase/GeoPackage Converter
Converts DWG and DXF files with annotations, multipatch, points, polygons, polylines, and text to GDB or GPKG
"""

import os
import sys
from osgeo import ogr, gdal

# Enable GDAL exceptions
gdal.UseExceptions()

def convert_cad_to_geo(input_file, output_path, output_format='GPKG'):
    """
    Convert DWG or DXF file to Geodatabase or GeoPackage
    Organizes features by their original CAD layer names
    
    Parameters:
    -----------
    input_file : str
        Path to input DWG or DXF file
    output_path : str
        Path to output file/directory
    output_format : str
        'GPKG' for GeoPackage or 'OpenFileGDB' for File Geodatabase
    """
    
    # Validate input file
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    # Check file extension
    file_ext = os.path.splitext(input_file)[1].lower()
    if file_ext not in ['.dwg', '.dxf']:
        raise ValueError(f"Unsupported file format: {file_ext}. Only .dwg and .dxf files are supported.")
    
    print(f"Opening CAD file: {input_file}")
    print(f"File type: {file_ext.upper()}")
    
    # Open CAD file
    cad_ds = ogr.Open(input_file, 0)  # 0 = read-only
    if cad_ds is None:
        raise Exception(f"Failed to open CAD file. Make sure GDAL has DWG/DXF support compiled.")
    
    print(f"CAD file opened successfully. Found {cad_ds.GetLayerCount()} source layers.")
    
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
    
    # Dictionary to organize features by CAD layer name and geometry type
    # Structure: {layer_name: {geom_type: [features]}}
    layer_features = {}
    layer_spatial_refs = {}
    layer_field_defs = {}
    
    print("\nReading and organizing features by original CAD layers...")
    
    # First pass: collect all features organized by their CAD layer attribute
    layer_count = cad_ds.GetLayerCount()
    total_features = 0
    
    for i in range(layer_count):
        source_layer = cad_ds.GetLayerByIndex(i)
        source_layer_name = source_layer.GetName()
        feature_count = source_layer.GetFeatureCount()
        
        print(f"\nReading source layer {i+1}/{layer_count}: {source_layer_name} ({feature_count} features)")
        
        if feature_count == 0:
            print(f"  Skipping empty layer")
            continue
        
        # Get spatial reference from source layer
        srs = source_layer.GetSpatialRef()
        
        # Get field definitions from source layer
        source_layer_defn = source_layer.GetLayerDefn()
        
        source_layer.ResetReading()
        for source_feature in source_layer:
            # Get the CAD layer name from the 'Layer' attribute
            cad_layer_name = source_feature.GetField('Layer') if source_feature.GetFieldIndex('Layer') >= 0 else 'DEFAULT'
            
            if cad_layer_name is None or cad_layer_name == '':
                cad_layer_name = 'DEFAULT'
            
            # Get geometry
            geom = source_feature.GetGeometryRef()
            if geom is None:
                continue
            
            geom_type = geom.GetGeometryType()
            
            # Initialize layer structure if needed
            if cad_layer_name not in layer_features:
                layer_features[cad_layer_name] = {}
                layer_spatial_refs[cad_layer_name] = srs
                layer_field_defs[cad_layer_name] = source_layer_defn
            
            if geom_type not in layer_features[cad_layer_name]:
                layer_features[cad_layer_name][geom_type] = []
            
            # Store feature data (geometry and attributes)
            feature_data = {
                'geometry': geom.Clone(),
                'attributes': {}
            }
            
            # Copy all attributes
            for j in range(source_layer_defn.GetFieldCount()):
                field_name = source_layer_defn.GetFieldDefn(j).GetName()
                field_value = source_feature.GetField(j)
                feature_data['attributes'][field_name] = field_value
            
            layer_features[cad_layer_name][geom_type].append(feature_data)
            total_features += 1
    
    print(f"\n{'='*60}")
    print(f"Found {len(layer_features)} unique CAD layers with {total_features} total features")
    print(f"{'='*60}")
    
    # Second pass: create output layers organized by CAD layer name
    converted_layers = 0
    
    for cad_layer_name in sorted(layer_features.keys()):
        geom_types = layer_features[cad_layer_name]
        srs = layer_spatial_refs[cad_layer_name]
        source_layer_defn = layer_field_defs[cad_layer_name]
        
        # Sanitize layer name for output
        clean_layer_name = cad_layer_name.replace(':', '_').replace(' ', '_').replace('-', '_').replace('/', '_')
        
        for geom_type, features in geom_types.items():
            if len(features) == 0:
                continue
            
            geom_type_name = ogr.GeometryTypeToName(geom_type)
            
            # If multiple geometry types exist in same layer, add suffix
            if len(geom_types) > 1:
                output_layer_name = f"{clean_layer_name}_{geom_type_name.replace(' ', '_')}"
            else:
                output_layer_name = clean_layer_name
            
            print(f"\nCreating output layer: {output_layer_name}")
            print(f"  Original CAD layer: {cad_layer_name}")
            print(f"  Geometry type: {geom_type_name}")
            print(f"  Feature count: {len(features)}")
            
            # Create output layer
            try:
                output_layer = output_ds.CreateLayer(
                    output_layer_name,
                    srs=srs,
                    geom_type=geom_type
                )
            except Exception as e:
                print(f"  Warning: Could not create layer {output_layer_name}: {e}")
                continue
            
            # Copy field definitions
            for j in range(source_layer_defn.GetFieldCount()):
                field_defn = source_layer_defn.GetFieldDefn(j)
                output_layer.CreateField(field_defn)
            
            # Add features to output layer
            output_layer_defn = output_layer.GetLayerDefn()
            features_copied = 0
            
            for feature_data in features:
                output_feature = ogr.Feature(output_layer_defn)
                
                # Set geometry
                output_feature.SetGeometry(feature_data['geometry'])
                
                # Set attributes
                for field_name, field_value in feature_data['attributes'].items():
                    field_index = output_feature.GetFieldIndex(field_name)
                    if field_index >= 0:
                        output_feature.SetField(field_index, field_value)
                
                output_layer.CreateFeature(output_feature)
                features_copied += 1
                output_feature = None
            
            print(f"  Copied {features_copied} features")
            converted_layers += 1
    
    # Clean up
    cad_ds = None
    output_ds = None
    
    print(f"\n{'='*60}")
    print(f"Conversion complete!")
    print(f"Created {converted_layers} output layers organized by original CAD layer names")
    print(f"Output saved to: {output_path}")
    print(f"{'='*60}")

def list_cad_layers(input_file):
    """
    List all layers in a DWG or DXF file with their properties
    Shows both GDAL layers and original CAD layer names
    """
    # Check file extension
    file_ext = os.path.splitext(input_file)[1].lower()
    if file_ext not in ['.dwg', '.dxf']:
        raise ValueError(f"Unsupported file format: {file_ext}. Only .dwg and .dxf files are supported.")
    
    cad_ds = ogr.Open(input_file, 0)
    if cad_ds is None:
        raise Exception(f"Failed to open CAD file: {input_file}")
    
    print(f"\nCAD File: {input_file}")
    print(f"File Type: {file_ext.upper()}")
    print(f"{'='*80}")
    print(f"Total GDAL layers: {cad_ds.GetLayerCount()}\n")
    
    # Collect unique CAD layer names
    cad_layer_names = set()
    
    for i in range(cad_ds.GetLayerCount()):
        layer = cad_ds.GetLayerByIndex(i)
        print(f"GDAL Layer {i+1}: {layer.GetName()}")
        print(f"  Geometry Type: {ogr.GeometryTypeToName(layer.GetGeomType())}")
        print(f"  Feature Count: {layer.GetFeatureCount()}")
        print(f"  Spatial Reference: {layer.GetSpatialRef()}")
        
        # Show field names
        layer_defn = layer.GetLayerDefn()
        if layer_defn.GetFieldCount() > 0:
            print(f"  Fields: {', '.join([layer_defn.GetFieldDefn(j).GetName() for j in range(layer_defn.GetFieldCount())])}")
        
        # Collect unique CAD layer names from features
        layer.ResetReading()
        layer_sample_size = min(10, layer.GetFeatureCount())
        for j, feature in enumerate(layer):
            if j >= layer_sample_size:
                break
            cad_layer = feature.GetField('Layer') if feature.GetFieldIndex('Layer') >= 0 else None
            if cad_layer:
                cad_layer_names.add(cad_layer)
        
        print()
    
    # Display unique original CAD layer names
    if cad_layer_names:
        print(f"{'='*80}")
        print(f"Original CAD Layers found (sampled): {len(cad_layer_names)}")
        print(f"{'='*80}")
        for cad_layer in sorted(cad_layer_names):
            print(f"  - {cad_layer}")
        print()
    
    cad_ds = None

def main():
    """
    Main function with interactive and command-line interface
    """
    print("="*60)
    print("DWG/DXF to Geodatabase/GeoPackage Converter")
    print("="*60)
    
    # Filter out Jupyter/IPython arguments like -f
    args = [arg for arg in sys.argv[1:] if not arg.startswith('-f')]
    
    # Check if command-line arguments were provided
    if len(args) >= 1:
        # Command-line mode
        input_file = args[0]
        
        # List layers only
        if len(args) == 2 and args[1] == '--list':
            try:
                list_cad_layers(input_file)
            except Exception as e:
                print(f"\nError: {e}")
                sys.exit(1)
            return
        
        # Convert with specified output
        if len(args) >= 2:
            output_path = args[1]
            
            # Determine output format
            if len(args) >= 3 and args[2] == '--gdb':
                output_format = 'OpenFileGDB'
                if not output_path.endswith('.gdb'):
                    output_path += '.gdb'
            else:
                output_format = 'GPKG'
                if not output_path.endswith('.gpkg'):
                    output_path += '.gpkg'
            
            try:
                convert_cad_to_geo(input_file, output_path, output_format)
            except Exception as e:
                print(f"\nError: {e}")
                sys.exit(1)
            return
    
    # Interactive mode - ask for input
    print("\nInteractive Mode")
    print("-" * 60)
    
    # Get input file
    while True:
        input_file = input("\nEnter the path to your DWG or DXF file: ").strip()
        
        # Remove quotes if user copied path with quotes
        input_file = input_file.strip('"').strip("'")
        
        if not input_file:
            print("Error: File path cannot be empty!")
            continue
        
        if not os.path.exists(input_file):
            print(f"Error: File not found: {input_file}")
            retry = input("Try again? (y/n): ").strip().lower()
            if retry != 'y':
                print("Conversion cancelled.")
                sys.exit(0)
            continue
        
        file_ext = os.path.splitext(input_file)[1].lower()
        if file_ext not in ['.dwg', '.dxf']:
            print(f"Error: File must be .dwg or .dxf (got {file_ext})")
            retry = input("Try again? (y/n): ").strip().lower()
            if retry != 'y':
                print("Conversion cancelled.")
                sys.exit(0)
            continue
        
        break
    
    # Ask if user wants to list layers first
    print("\n" + "-" * 60)
    list_first = input("Do you want to list layers first? (y/n): ").strip().lower()
    
    if list_first == 'y':
        try:
            list_cad_layers(input_file)
        except Exception as e:
            print(f"\nError listing layers: {e}")
        
        print("\n" + "-" * 60)
        continue_convert = input("Continue with conversion? (y/n): ").strip().lower()
        if continue_convert != 'y':
            print("Conversion cancelled.")
            sys.exit(0)
    
    # Get output format
    print("\n" + "-" * 60)
    print("Select output format:")
    print("  1. GeoPackage (.gpkg) - recommended")
    print("  2. File Geodatabase (.gdb)")
    
    while True:
        format_choice = input("\nEnter choice (1 or 2): ").strip()
        
        if format_choice == '1':
            output_format = 'GPKG'
            default_ext = '.gpkg'
            break
        elif format_choice == '2':
            output_format = 'OpenFileGDB'
            default_ext = '.gdb'
            break
        else:
            print("Invalid choice! Please enter 1 or 2.")
    
    # Get output file path
    print("\n" + "-" * 60)
    input_basename = os.path.splitext(os.path.basename(input_file))[0]
    suggested_output = input_basename + "_converted" + default_ext
    
    print(f"Suggested output name: {suggested_output}")
    output_path = input(f"Enter output file path (press Enter for default): ").strip()
    
    # Remove quotes if present
    output_path = output_path.strip('"').strip("'")
    
    if not output_path:
        output_path = suggested_output
    
    # Ensure correct extension
    if not output_path.endswith(default_ext):
        output_path += default_ext
    
    # Confirm before converting
    print("\n" + "=" * 60)
    print("CONVERSION SUMMARY:")
    print("-" * 60)
    print(f"Input file:     {input_file}")
    print(f"Output file:    {output_path}")
    print(f"Output format:  {output_format}")
    print("=" * 60)
    
    confirm = input("\nProceed with conversion? (y/n): ").strip().lower()
    
    if confirm != 'y':
        print("Conversion cancelled.")
        sys.exit(0)
    
    # Perform conversion
    try:
        print()
        convert_cad_to_geo(input_file, output_path, output_format)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
