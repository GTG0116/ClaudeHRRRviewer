#!/usr/bin/env python3
"""
Test script to verify HRRR viewer dependencies and S3 access
"""

import sys

def test_imports():
    """Test that all required packages can be imported"""
    print("Testing package imports...")
    packages = {
        'numpy': 'numpy',
        'matplotlib': 'matplotlib',
        'cartopy': 'cartopy',
        'xarray': 'xarray',
        'cfgrib': 'cfgrib',
        's3fs': 's3fs'
    }
    
    failed = []
    for name, module in packages.items():
        try:
            __import__(module)
            print(f"✓ {name}")
        except ImportError as e:
            print(f"✗ {name}: {e}")
            failed.append(name)
    
    if failed:
        print(f"\n❌ Failed to import: {', '.join(failed)}")
        return False
    else:
        print("\n✓ All packages imported successfully!")
        return True

def test_s3_access():
    """Test S3 access to NOAA HRRR bucket"""
    print("\nTesting S3 access...")
    try:
        import s3fs
        from datetime import datetime, timedelta
        
        s3 = s3fs.S3FileSystem(anon=True)
        
        # Try to list a recent HRRR directory
        test_date = (datetime.utcnow() - timedelta(days=1)).strftime('%Y%m%d')
        test_path = f"noaa-hrrr-bdp-pds/hrrr.{test_date}/conus/"
        
        files = s3.ls(test_path)
        if files:
            print(f"✓ Successfully accessed NOAA HRRR bucket")
            print(f"  Found {len(files)} files for {test_date}")
            return True
        else:
            print(f"✗ No files found in {test_path}")
            return False
            
    except Exception as e:
        print(f"✗ S3 access failed: {e}")
        return False

def test_eccodes():
    """Test eccodes library"""
    print("\nTesting eccodes...")
    try:
        import eccodes
        print(f"✓ eccodes version: {eccodes.__version__}")
        return True
    except ImportError:
        print("✗ eccodes not found - this is required for GRIB2 decoding")
        print("  Install with: sudo apt-get install libeccodes-dev (Linux)")
        print("  or: brew install eccodes (macOS)")
        return False
    except Exception as e:
        print(f"✗ eccodes error: {e}")
        return False

def main():
    """Run all tests"""
    print("="*60)
    print("HRRR Viewer Dependency Test")
    print("="*60 + "\n")
    
    results = []
    results.append(("Package Imports", test_imports()))
    results.append(("eccodes", test_eccodes()))
    results.append(("S3 Access", test_s3_access()))
    
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("="*60 + "\n")
    
    if all_passed:
        print("🎉 All tests passed! Ready to run hrrr_viewer.py")
        return 0
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
