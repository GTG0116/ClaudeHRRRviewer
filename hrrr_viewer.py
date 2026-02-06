#!/usr/bin/env python3
"""
Quick diagnostic to test HRRR data access and identify issues
"""

import sys
import time
from datetime import datetime, timedelta
import s3fs

def test_s3_connection():
    """Test basic S3 connectivity"""
    print("1. Testing S3 connection...")
    try:
        s3 = s3fs.S3FileSystem(anon=True)
        print("   ✓ S3 connection established")
        return s3
    except Exception as e:
        print(f"   ✗ S3 connection failed: {e}")
        return None

def find_latest_hrrr_run(s3):
    """Find the most recent available HRRR run"""
    print("\n2. Finding latest available HRRR run...")
    
    # Start from 6 hours ago and work backwards
    for hours_back in range(2, 24):
        check_time = datetime.utcnow() - timedelta(hours=hours_back)
        check_time = check_time.replace(minute=0, second=0, microsecond=0)
        
        date_str = check_time.strftime('%Y%m%d')
        hour_str = check_time.strftime('%H')
        
        # Check if this directory exists
        path = f"noaa-hrrr-bdp-pds/hrrr.{date_str}/conus/"
        
        try:
            files = s3.ls(path)
            # Look for f00 file
            test_file = f"noaa-hrrr-bdp-pds/hrrr.{date_str}/conus/hrrr.t{hour_str}z.wrfsfcf00.grib2"
            if test_file in files:
                print(f"   ✓ Found run: {check_time.strftime('%Y-%m-%d %H:00 UTC')}")
                print(f"   Directory: {path}")
                print(f"   Files available: {len(files)}")
                return check_time, path
        except:
            continue
    
    print("   ✗ No recent HRRR runs found")
    return None, None

def test_single_file_download(s3, model_time):
    """Test downloading and decoding a single file"""
    print("\n3. Testing single file download and decode...")
    
    date_str = model_time.strftime('%Y%m%d')
    hour_str = model_time.strftime('%H')
    s3_path = f"noaa-hrrr-bdp-pds/hrrr.{date_str}/conus/hrrr.t{hour_str}z.wrfsfcf00.grib2"
    
    print(f"   File: {s3_path}")
    
    try:
        # Check file size first
        info = s3.info(s3_path)
        size_mb = info['size'] / (1024 * 1024)
        print(f"   File size: {size_mb:.1f} MB")
        
        # Time the download
        start = time.time()
        print("   Downloading...", end='', flush=True)
        
        with s3.open(s3_path, 'rb') as f:
            data = f.read()
        
        download_time = time.time() - start
        print(f" done ({download_time:.1f}s)")
        
        # Try to decode with cfgrib
        print("   Decoding GRIB2...", end='', flush=True)
        decode_start = time.time()
        
        import xarray as xr
        import tempfile
        
        # Write to temp file
        with tempfile.NamedTemporaryFile(suffix='.grib2', delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        
        try:
            ds = xr.open_dataset(tmp_path, engine='cfgrib',
                                backend_kwargs={
                                    'filter_by_keys': {
                                        'typeOfLevel': 'heightAboveGround',
                                        'level': 2
                                    }
                                })
            
            decode_time = time.time() - decode_start
            print(f" done ({decode_time:.1f}s)")
            
            # Check what we got
            if 't2m' in ds:
                temp_var = 't2m'
            elif 't' in ds:
                temp_var = 't'
            else:
                print(f"   ✗ Temperature variable not found. Available: {list(ds.data_vars)}")
                return False
            
            print(f"   ✓ Found temperature: {temp_var}")
            print(f"   Grid size: {ds[temp_var].shape}")
            
            import os
            os.unlink(tmp_path)
            
            total_time = download_time + decode_time
            print(f"\n   Total time: {total_time:.1f}s")
            print(f"   Estimated for 49 files (sequential): {total_time * 49 / 60:.1f} minutes")
            print(f"   Estimated for 49 files (4 workers): {total_time * 49 / 4 / 60:.1f} minutes")
            
            return True
            
        except Exception as e:
            print(f"\n   ✗ Decode failed: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"\n   ✗ Download failed: {e}")
        return False

def main():
    print("="*70)
    print("HRRR Viewer Diagnostic Tool")
    print("="*70)
    print()
    
    # Test S3
    s3 = test_s3_connection()
    if not s3:
        print("\n❌ Cannot proceed without S3 connection")
        return 1
    
    # Find latest run
    model_time, path = find_latest_hrrr_run(s3)
    if not model_time:
        print("\n❌ Cannot find HRRR data")
        return 1
    
    # Test download/decode
    success = test_single_file_download(s3, model_time)
    
    print("\n" + "="*70)
    if success:
        print("✓ All tests passed!")
        print("\nRecommendations:")
        print("- Start with HRRR_TEST_MODE=true to test 3 hours")
        print("- Use HRRR_NUM_WORKERS=1 for sequential (more reliable)")
        print("- Use HRRR_NUM_WORKERS=4 for parallel (faster)")
    else:
        print("❌ Tests failed - check errors above")
    print("="*70)
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
