#!/usr/bin/env python3
"""
HRRR Weather Model Viewer
Fetches HRRR GRIB2 files from AWS S3, decodes them, and generates temperature visualizations
"""

import os
import sys
from datetime import datetime, timedelta
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import s3fs
import xarray as xr
import cfgrib
from pathlib import Path

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
        """Download GRIB2 file from S3 and extract temperature data"""
        print(f"Processing forecast hour {forecast_hour}...")
        print(f"S3 path: {s3_path}")
        
        try:
            # Open file directly from S3
            with self.s3.open(s3_path, 'rb') as f:
                # Read GRIB2 file using cfgrib
                ds = xr.open_dataset(f, engine='cfgrib', 
                                    backend_kwargs={'filter_by_keys': {'typeOfLevel': 'surface', 'shortName': 't'}})
                
                # Extract temperature (convert from Kelvin to Fahrenheit)
                temp_k = ds['t'].values
                temp_f = (temp_k - 273.15) * 9/5 + 32
                
                # Get coordinates
                lats = ds['latitude'].values
                lons = ds['longitude'].values
                
                return temp_f, lats, lons, ds
                
        except Exception as e:
            print(f"Error processing {s3_path}: {e}")
            return None, None, None, None
    
    def create_temperature_map(self, temp_f, lats, lons, model_time, forecast_hour):
        """Create a temperature visualization map"""
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
        plt.close()
        
        print(f"Saved: {filepath}")
        return filepath
    
    def process_full_run(self, max_forecast_hours=48):
        """Process full HRRR model run (0-48 hours)"""
        model_time = self.get_latest_model_run()
        print(f"\n{'='*60}")
        print(f"HRRR Model Viewer")
        print(f"Model Run: {model_time.strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"Processing forecast hours: 0-{max_forecast_hours}")
        print(f"{'='*60}\n")
        
        generated_files = []
        
        for forecast_hour in range(0, max_forecast_hours + 1):
            s3_path = self.construct_s3_path(model_time, forecast_hour)
            
            temp_f, lats, lons, ds = self.download_and_process_grib(s3_path, forecast_hour)
            
            if temp_f is not None:
                filepath = self.create_temperature_map(temp_f, lats, lons, 
                                                       model_time, forecast_hour)
                generated_files.append(filepath)
            else:
                print(f"Skipping forecast hour {forecast_hour} due to errors")
        
        print(f"\n{'='*60}")
        print(f"Processing Complete!")
        print(f"Generated {len(generated_files)} images in {self.output_dir}")
        print(f"{'='*60}\n")
        
        return generated_files

def main():
    """Main execution function"""
    # Set forecast hours (default 48, can be overridden by environment variable)
    max_hours = int(os.getenv('HRRR_MAX_HOURS', '48'))
    
    viewer = HRRRViewer()
    viewer.process_full_run(max_forecast_hours=max_hours)

if __name__ == '__main__':
    main()
