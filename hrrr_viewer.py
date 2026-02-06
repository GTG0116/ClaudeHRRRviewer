#!/usr/bin/env python3
"""
HRRR Weather Model Viewer
Fetches HRRR GRIB2 files from AWS S3, decodes them, and generates temperature visualizations
Uses parallel processing for faster execution
"""

import os
import sys
from datetime import datetime, timedelta
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for parallel processing
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import s3fs
import xarray as xr
import cfgrib
from pathlib import Path
from multiprocessing import Pool, cpu_count
from functools import partial
import signal
from contextlib import contextmanager
import traceback

class TimeoutException(Exception):
    pass

@contextmanager
def timeout(seconds):
    """Context manager for timeout"""
    def timeout_handler(signum, frame):
        raise TimeoutException(f"Operation timed out after {seconds} seconds")
    
    # Set the signal handler
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

class HRRRViewer:
    def __init__(self, output_dir='output'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.s3 = s3fs.S3FileSystem(anon=True)
        
    def get_latest_model_run(self):
        """Get the latest available HRRR model run time"""
        now = datetime.utcnow()
        # HRRR runs are typically available 1-2 hours after model time
        model_time = now - timedelta(hours=3)
        # Round down to nearest hour
        model_time = model_time.replace(minute=0, second=0, microsecond=0)
        return model_time
    
    def construct_s3_path(self, model_time, forecast_hour):
        """
        Construct S3 path for HRRR GRIB2 file
        Format: s3://noaa-hrrr-bdp-pds/hrrr.YYYYMMDD/conus/hrrr.tHHz.wrfsfcf{forecast_hour}.grib2
        """
        date_str = model_time.strftime('%Y%m%d')
        hour_str = model_time.strftime('%H')
        
        s3_path = f"noaa-hrrr-bdp-pds/hrrr.{date_str}/conus/hrrr.t{hour_str}z.wrfsfcf{forecast_hour:02d}.grib2"
        return s3_path
    
    def download_and_process_grib(self, s3_path, forecast_hour):
        """Download GRIB2 file from S3 and extract temperature data with timeout"""
        print(f"[F{forecast_hour:02d}] Processing...", flush=True)
        
        try:
            with timeout(60):  # 60 second timeout per file
                # Open file directly from S3
                with self.s3.open(s3_path, 'rb') as f:
                    # Read GRIB2 file using cfgrib
                    # Filter for 2-meter temperature
                    ds = xr.open_dataset(f, engine='cfgrib', 
                                        backend_kwargs={
                                            'filter_by_keys': {
                                                'typeOfLevel': 'heightAboveGround',
                                                'level': 2
                                            }
                                        })
                    
                    # Extract temperature (convert from Kelvin to Fahrenheit)
                    temp_k = ds['t2m'].values if 't2m' in ds else ds['t'].values
                    temp_f = (temp_k - 273.15) * 9/5 + 32
                    
                    # Get coordinates
                    lats = ds['latitude'].values
                    lons = ds['longitude'].values
                    
                    print(f"[F{forecast_hour:02d}] ✓ Decoded", flush=True)
                    return temp_f, lats, lons, ds
                
        except TimeoutException as e:
            print(f"[F{forecast_hour:02d}] ✗ Timeout: {e}", flush=True)
            return None, None, None, None
        except FileNotFoundError:
            print(f"[F{forecast_hour:02d}] ✗ File not found: {s3_path}", flush=True)
            return None, None, None, None
        except Exception as e:
            print(f"[F{forecast_hour:02d}] ✗ Error: {type(e).__name__}: {str(e)[:100]}", flush=True)
            traceback.print_exc()
            return None, None, None, None
    
    def create_temperature_map(self, temp_f, lats, lons, model_time, forecast_hour):
        """Create a temperature visualization map with timeout"""
        try:
            with timeout(30):  # 30 second timeout for plotting
                valid_time = model_time + timedelta(hours=forecast_hour)
                
                fig = plt.figure(figsize=(14, 10))
                ax = plt.axes(projection=ccrs.LambertConformal())
                
                # Set extent to CONUS
                ax.set_extent([-125, -66, 24, 50], crs=ccrs.PlateCarree())
                
                # Add map features
                ax.add_feature(cfeature.COASTLINE, linewidth=0.5)
                ax.add_feature(cfeature.STATES, linewidth=0.3)
                ax.add_feature(cfeature.BORDERS, linewidth=0.5)
                
                # Plot temperature
                levels = np.arange(-40, 121, 5)
                cf = ax.contourf(lons, lats, temp_f, levels=levels,
                                transform=ccrs.PlateCarree(),
                                cmap='RdYlBu_r', extend='both')
                
                # Add colorbar
                cbar = plt.colorbar(cf, ax=ax, orientation='horizontal', 
                                   pad=0.05, aspect=50, shrink=0.8)
                cbar.set_label('Temperature (°F)', fontsize=12, weight='bold')
                
                # Add title
                title = f'HRRR Surface Temperature\n'
                title += f'Model Run: {model_time.strftime("%Y-%m-%d %H:%M UTC")}\n'
                title += f'Valid: {valid_time.strftime("%Y-%m-%d %H:%M UTC")} (F{forecast_hour:02d})'
                plt.title(title, fontsize=14, weight='bold', pad=20)
                
                # Save figure
                filename = f'hrrr_temp_f{forecast_hour:02d}.png'
                filepath = self.output_dir / filename
                plt.savefig(filepath, dpi=150, bbox_inches='tight')
                plt.close(fig)
                
                print(f"[F{forecast_hour:02d}] ✓ Saved: {filename}", flush=True)
                return filepath
                
        except TimeoutException as e:
            print(f"[F{forecast_hour:02d}] ✗ Plot timeout", flush=True)
            plt.close('all')
            return None
        except Exception as e:
            print(f"[F{forecast_hour:02d}] ✗ Plot error: {type(e).__name__}", flush=True)
            plt.close('all')
            return None
    
    def process_single_hour(self, model_time, forecast_hour):
        """Process a single forecast hour (designed for parallel execution)"""
        try:
            s3_path = self.construct_s3_path(model_time, forecast_hour)
            
            temp_f, lats, lons, ds = self.download_and_process_grib(s3_path, forecast_hour)
            
            if temp_f is not None:
                filepath = self.create_temperature_map(temp_f, lats, lons, 
                                                       model_time, forecast_hour)
                if filepath:
                    return (forecast_hour, filepath, True)
                else:
                    return (forecast_hour, None, False)
            else:
                return (forecast_hour, None, False)
                
        except Exception as e:
            print(f"[F{forecast_hour:02d}] ✗ Unexpected error: {e}", flush=True)
            return (forecast_hour, None, False)
    
    def process_full_run(self, max_forecast_hours=48, num_workers=None):
        """
        Process full HRRR model run (0-48 hours) using parallel processing
        
        Args:
            max_forecast_hours: Maximum forecast hour to process (default: 48)
            num_workers: Number of parallel workers (default: cpu_count)
        """
        model_time = self.get_latest_model_run()
        
        # Determine number of workers
        if num_workers is None:
            num_workers = min(cpu_count(), 8)  # Cap at 8 to avoid overwhelming S3
        
        print(f"\n{'='*60}")
        print(f"HRRR Model Viewer (Parallel Processing)")
        print(f"Model Run: {model_time.strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"Processing forecast hours: 0-{max_forecast_hours}")
        print(f"Parallel workers: {num_workers}")
        print(f"{'='*60}\n")
        
        # Create list of forecast hours to process
        forecast_hours = list(range(0, max_forecast_hours + 1))
        
        # Create partial function with model_time bound
        process_func = partial(self.process_single_hour, model_time)
        
        # Process in parallel with timeout
        generated_files = []
        failed_hours = []
        
        try:
            with Pool(processes=num_workers) as pool:
                # Use imap_unordered for better progress tracking
                results = pool.imap_unordered(process_func, forecast_hours)
                
                # Collect results as they complete
                completed = 0
                for result in results:
                    forecast_hour, filepath, success = result
                    completed += 1
                    
                    if success and filepath is not None:
                        generated_files.append((forecast_hour, filepath))
                    else:
                        failed_hours.append(forecast_hour)
                    
                    # Progress update every 5 hours
                    if completed % 5 == 0:
                        print(f"\n--- Progress: {completed}/{len(forecast_hours)} complete ---\n", flush=True)
            
            # Sort by forecast hour
            generated_files.sort(key=lambda x: x[0])
            generated_files = [f[1] for f in generated_files]
            
        except Exception as e:
            print(f"\n✗ Critical error in parallel processing: {e}")
            traceback.print_exc()
        
        print(f"\n{'='*60}")
        print(f"Processing Complete!")
        print(f"Successfully generated: {len(generated_files)}/{len(forecast_hours)} images")
        if failed_hours:
            print(f"Failed hours: {sorted(failed_hours)}")
        print(f"Output directory: {self.output_dir}")
        print(f"{'='*60}\n")
        
        return generated_files

def main():
    """Main execution function"""
    # Set forecast hours (default 48, can be overridden by environment variable)
    max_hours = int(os.getenv('HRRR_MAX_HOURS', '48'))
    
    # Set number of workers (default auto-detect, can be overridden)
    # Set to 1 for sequential processing
    num_workers = os.getenv('HRRR_NUM_WORKERS')
    if num_workers:
        num_workers = int(num_workers)
    else:
        num_workers = None  # Auto-detect
    
    # Test mode - only process first 3 hours for quick validation
    test_mode = os.getenv('HRRR_TEST_MODE', 'false').lower() == 'true'
    if test_mode:
        print("⚠️  TEST MODE: Processing only first 3 hours")
        max_hours = 2
        num_workers = 1
    
    viewer = HRRRViewer()
    viewer.process_full_run(max_forecast_hours=max_hours, num_workers=num_workers)

if __name__ == '__main__':
    main()
