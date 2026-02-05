# HRRR Weather Model Viewer

A Python-based weather model viewer that fetches High-Resolution Rapid Refresh (HRRR) GRIB2 files from AWS S3, decodes them, and generates temperature visualizations as PNG images. Designed to run automatically on GitHub Actions.

## Features

- 🌡️ Fetches HRRR surface temperature data from NOAA's AWS S3 bucket
- 📊 Decodes GRIB2 files using cfgrib/eccodes
- 🗺️ Generates high-quality PNG visualizations with Cartopy
- ⏱️ Processes full model runs (0-48 forecast hours)
- 🤖 Automated execution via GitHub Actions
- 📱 Deploys interactive gallery to GitHub Pages

## How It Works

1. **Data Source**: HRRR data is accessed from `s3://noaa-hrrr-bdp-pds/` (public NOAA bucket)
2. **Processing**: GRIB2 files are decoded to extract 2-meter temperature
3. **Visualization**: Temperature data is plotted on a Lambert Conformal map projection
4. **Automation**: GitHub Actions runs the workflow every 6 hours and deploys to GitHub Pages

## Setup Instructions

### 1. Fork/Clone this Repository

```bash
git clone https://github.com/yourusername/hrrr-weather-viewer.git
cd hrrr-weather-viewer
```

### 2. Local Setup (Optional)

If you want to run locally:

```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y libeccodes-dev libproj-dev libgeos-dev

# Install Python dependencies
pip install -r requirements.txt

# Run the viewer
python hrrr_viewer.py
```

### 3. GitHub Actions Setup

The workflow is already configured in `.github/workflows/hrrr-viewer.yml`. To enable it:

1. **Push to GitHub**:
   ```bash
   git add .
   git commit -m "Initial commit"
   git push origin main
   ```

2. **Enable GitHub Actions**:
   - Go to your repository's "Actions" tab
   - Enable workflows if prompted

3. **Enable GitHub Pages** (optional, for web gallery):
   - Go to Settings → Pages
   - Source: Deploy from a branch
   - Branch: `gh-pages` / `root`
   - Save

4. **Manual Trigger** (optional):
   - Go to Actions → HRRR Weather Model Viewer
   - Click "Run workflow"
   - Optionally specify max forecast hours

## Configuration

### Environment Variables

- `HRRR_MAX_HOURS`: Maximum forecast hours to process (default: 48)

### Workflow Schedule

The workflow runs automatically every 6 hours. To change this, edit `.github/workflows/hrrr-viewer.yml`:

```yaml
schedule:
  - cron: '0 */6 * * *'  # Every 6 hours
```

## Output

### PNG Files

Temperature maps are saved as:
- `hrrr_temp_f00.png` (analysis time)
- `hrrr_temp_f01.png` (forecast hour 1)
- `hrrr_temp_f02.png` (forecast hour 2)
- ... up to `hrrr_temp_f48.png`

### GitHub Pages Gallery

If enabled, an interactive HTML gallery is deployed to:
`https://yourusername.github.io/hrrr-weather-viewer/`

## Project Structure

```
hrrr-weather-viewer/
├── .github/
│   └── workflows/
│       └── hrrr-viewer.yml    # GitHub Actions workflow
├── hrrr_viewer.py              # Main Python script
├── requirements.txt            # Python dependencies
├── README.md                   # This file
└── output/                     # Generated PNG files (created automatically)
```

## HRRR Data Information

- **Model**: High-Resolution Rapid Refresh (HRRR)
- **Resolution**: 3 km
- **Coverage**: Continental United States (CONUS)
- **Update Frequency**: Hourly
- **Forecast Length**: 48 hours
- **Data Source**: NOAA Big Data Program (AWS S3)

## Troubleshooting

### GRIB2 Files Not Found

HRRR data may have a delay of 1-3 hours. The script automatically looks for data from 3 hours ago.

### Installation Issues

**eccodes errors**:
```bash
# Ubuntu/Debian
sudo apt-get install libeccodes-dev

# macOS
brew install eccodes
```

**cartopy errors**:
```bash
# Ubuntu/Debian
sudo apt-get install libproj-dev libgeos-dev

# macOS
brew install proj geos
```

### GitHub Actions Failures

- Check the Actions tab for detailed error logs
- Ensure all dependencies are in `requirements.txt`
- System dependencies are installed in the workflow file

## Customization Ideas

1. **Add More Variables**: Modify to show wind, precipitation, or pressure
2. **Different Levels**: Access upper-air data (500mb, 850mb, etc.)
3. **Animation**: Create animated GIFs from the forecast sequence
4. **Email Alerts**: Add notification steps for severe weather
5. **Regional Focus**: Adjust map extent for specific regions

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the MIT License.

## Acknowledgments

- NOAA for providing open access to HRRR data
- ECMWF for the eccodes library
- The Python geospatial community (xarray, cartopy, etc.)

## Resources

- [HRRR Data Documentation](https://www.nco.ncep.noaa.gov/pmb/products/hrrr/)
- [NOAA Big Data Program](https://registry.opendata.aws/noaa-hrrr-pds/)
- [cfgrib Documentation](https://github.com/ecmwf/cfgrib)
- [Cartopy Documentation](https://scitools.org.uk/cartopy/)
