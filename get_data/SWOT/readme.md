# SWOT Data Downloader

This script is used to download and subset SWOT (Surface Water and Ocean Topography) satellite data from the AVISO FTP server.

## Key Parameters
- **Cycle number**: Identifies the repeat cycle of the satellite orbit (e.g., `cycle_001`). Each cycle represents a full repeat of the ground track.  
- **Pass number (half orbit)**: Identifies a specific pass (track) within a cycle, e.g., an ascending or descending orbit segment.  

By specifying cycle numbers and pass numbers, users can target only the required data instead of downloading the entire archive.

## Features
- Automatic FTP connection and file download.  
- Option to select the latest version of files or all available versions.  
- Subsetting of data by geographic bounding box (latitude/longitude).  
- Basic visualization of variables such as SSH (sea surface height).  

## Example Usage
```python
files = ftp_download_files(
    ftp_path="/swot/l2/ssh/",
    level="L2",
    variant="NOMINAL",
    cycle_numbers=[3],
    half_orbits=[150],
    output_dir="./data",
    only_last=True
)
