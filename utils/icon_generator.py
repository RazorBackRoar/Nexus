#!/usr/bin/env python3
"""
macOS Icon Generator for py2app
Converts existing .icns file to proper format with all required sizes
"""
import os
import sys
from PIL import Image
import subprocess
import shutil

def extract_png_from_icns(icns_path, output_path, size=1024):
    """
    Extract the largest PNG from an .icns file using sips (macOS built-in tool)
    
    Args:
        icns_path (str): Path to the input .icns file
        output_path (str): Where to save the extracted PNG
        size (int): Target size for the extracted image (default 1024x1024)
    
    Returns:
        bool: True if extraction successful, False otherwise
    """
    try:
        # sips is a macOS command-line tool for image processing
        # -s format png: Set output format to PNG
        # --resampleWidth: Resize to specified width (maintains aspect ratio)
        cmd = ['sips', '-s', 'format', 'png', '--resampleWidth', str(size), icns_path, '--out', output_path]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"   ✅ Extracted {size}x{size} PNG from {os.path.basename(icns_path)}")
            return True
        else:
            print(f"   ❌ sips failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error extracting PNG: {e}")
        return False

def create_icns_from_png(png_path, output_icns):
    """
    Create a proper .icns file from PNG using iconutil (macOS built-in tool)
    
    This function creates all the required icon sizes that macOS expects:
    - Standard sizes: 16x16, 32x32, 128x128, 256x256, 512x512
    - Retina (@2x) versions for high-DPI displays
    
    Args:
        png_path (str): Path to the source PNG file
        output_icns (str): Path where the final .icns file should be saved
    
    Returns:
        bool: True if creation successful, False otherwise
    """
    try:
        # Create a .iconset directory - this is what iconutil expects
        iconset_dir = png_path.replace('.png', '.iconset')
        os.makedirs(iconset_dir, exist_ok=True)
        
        # Define all required icon sizes for macOS
        # Format: (pixel_size, filename_in_iconset)
        sizes = [
            (16, 'icon_16x16.png'),           # Small icons (Finder, etc.)
            (32, 'icon_16x16@2x.png'),        # 16x16 Retina version
            (32, 'icon_32x32.png'),           # Standard 32x32
            (64, 'icon_32x32@2x.png'),        # 32x32 Retina version
            (128, 'icon_128x128.png'),        # Standard 128x128
            (256, 'icon_128x128@2x.png'),     # 128x128 Retina version
            (256, 'icon_256x256.png'),        # Standard 256x256
            (512, 'icon_256x256@2x.png'),     # 256x256 Retina version
            (512, 'icon_512x512.png'),        # Standard 512x512
            (1024, 'icon_512x512@2x.png')     # 512x512 Retina version (largest)
        ]
        
        # Open the source PNG and ensure it has transparency (RGBA)
        with Image.open(png_path) as img:
            if img.mode != 'RGBA':
                # Convert to RGBA to preserve transparency
                img = img.convert('RGBA')
            
            # Create each required size
            for size, filename in sizes:
                # Use LANCZOS resampling for high-quality resizing
                resized = img.resize((size, size), Image.Resampling.LANCZOS)
                resized.save(os.path.join(iconset_dir, filename), 'PNG')
        
        print(f"   ✅ Created all {len(sizes)} icon sizes in iconset")
        
        # Use iconutil to convert the .iconset directory to .icns file
        cmd = ['iconutil', '-c', 'icns', iconset_dir, '-o', output_icns]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Clean up the temporary .iconset directory
            shutil.rmtree(iconset_dir)
            print(f"   ✅ Successfully created {output_icns}")
            return True
        else:
            print(f"   ❌ iconutil failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error creating icns: {e}")
        return False

def main():
    """
    Main function that orchestrates the icon conversion process
    """
    # Check if we have the right number of command-line arguments
    if len(sys.argv) != 3:
        print("Usage: python icon_generator.py <input.icns> <output.icns>")
        print("Example: python icon_generator.py original.icns converted.icns")
        sys.exit(1)
    
    input_icns = sys.argv[1]
    output_icns = sys.argv[2]
    
    # Verify the input file exists
    if not os.path.exists(input_icns):
        print(f"   ❌ Input file not found: {input_icns}")
        sys.exit(1)
    
    print(f"🔄 Converting {input_icns} to {output_icns}")
    
    # Step 1: Extract a high-quality PNG from the original .icns
    temp_png = "temp_icon_1024.png"
    print("   Step 1: Extracting PNG from original .icns file...")
    
    if not extract_png_from_icns(input_icns, temp_png):
        print("   ❌ Failed to extract PNG from .icns file")
        sys.exit(1)
    
    # Step 2: Create a new .icns file with all proper sizes
    print("   Step 2: Creating new .icns with all required sizes...")
    
    if create_icns_from_png(temp_png, output_icns):
        # Clean up temporary file
        os.remove(temp_png)
        print(f"   🎉 Successfully created {output_icns}")
    else:
        # Clean up on failure
        if os.path.exists(temp_png):
            os.remove(temp_png)
        print("   ❌ Failed to create new .icns file")
        sys.exit(1)

# This is the corrected line - note the double underscores
if __name__ == "__main__":
    main()