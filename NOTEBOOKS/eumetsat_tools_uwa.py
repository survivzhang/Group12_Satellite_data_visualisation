import configparser      # a library that allows us to parse standard configuration files
import IPython           # a library that helps us display video and HTML content
import shutil            # a library that allows us access to basic operating system commands like copy
import zipfile           # a library that allows us to unzip zip-files.
from pathlib import Path # a library that helps construct system path objects
import getpass           # a library to help us enter passwords
from cartopy.feature.nightshade import Nightshade # a library that helps plot day/night cycles
import datetime                                   # a library that supports time and dat objects
from matplotlib.colors import ListedColormap      # a library that extends plotting support
import warnings                                   # a library that helps us parse XML files
import eumartools                                 # a library that helps us manage warnings
import xml.etree.ElementTree as ET                # a EUMETSAT library that support working with Sentinel-3 products

import os                # a library that allows us access to basic operating system commands like making directories
import eumdac            # a tool that helps us download via the eumetsat/data-store
import matplotlib.pyplot as plt                   # a library that support plotting
import cartopy                                    # a library that support mapping
import glob                                       # a library that aids in searching for files
import matplotlib.ticker as mticker               # a library that extends plotting support
import numpy as np                                # a library that provides support for array-based mathematics
import xarray as xr                               # a library that supports the use of multi-dimensional arrays in Python
import numpy as np 

import requests

#这段代码主要是为 EUMETSAT Sentinel-3 SLSTR 卫星数据（特别是海表温度 SST）做下载、读取、解析和绘图的工具集
#整体来看，这是一套针对 Sentinel-3 SLSTR 海表温度（SST）产品 的处理管道：

#登录 EUMETSAT API

#根据产品名解析元数据

#从 SAFE 目录加载 .nc 数据

#修正时间变量

#用 Cartopy 绘制地图

def login():
    
    cred_file = '/home/andrew/eumetsat_api_credentials.txt'
    # os.path.exists(cred_file)

    with open(cred_file, 'r') as f:
        lines = f.readlines()
        consumer_key = lines[2].strip()
        consumer_secret = lines[3].strip()

    # Insert your personal key and secret into the single quotes

    credentials = (consumer_key, consumer_secret)

    token = eumdac.AccessToken(credentials)

    try:
        print(f"This token '{token}' expires {token.expiration}")
    except requests.exceptions.HTTPError as error:
        print(f"Error when tryng the request to the server: '{error}'")

    return token

def parse_product_name(product_id):
    """
    Parse the product ID to extract the metadata.

    Format is: 
    
    `MMM_SL_L_TTTTTT_yyyymmddThhmmss_YYYYMMDDTHHMMSS_YYYYMMDDTHHMMSS_[instance ID]_GGG_<class ID>.<extension> `

    Here's a breakdown of each component: 
    - MMM: Mission ID (e.g., S3A, S3B for Sentinel-3A and Sentinel-3B respectively).
    - SL: Data source/consumer (e.g., SL for SLSTR).
    - L: Processing level (0 for Level-0, 1 for Level-1, 2 for Level-2).
    - TTTTTT: Data Type ID (e.g., SLT for SLSTR Level-0, RBT for Level-1, WCT, WST, LST, FRP for Level-2).
    - yyyymmddThhmmss: Sensing start time (ISO 8601 format).
    - YYYYMMDDTHHMMSS: Sensing stop time (ISO 8601 format).
    - YYYYMMDDTHHMMSS: Product creation date.
    - [instance ID]: A unique 17-character identifier.
    - .SEN3: Filename extension.

    `instance ID` is DDDD_CCC_LLL_FFFF:
    - DDDD: Duration of the sensing interval in seconds.
    - CCC: Cycle number at the sensing start time.
    - LLL: Relative orbit number.
    - FFFF: Frame number.

    GGG–Product Generating Centre

    - 'MAR' for Marine Processing and Archiving Centre (EUMETSAT)
    - 'LN3' for Land Surface Topography Mission Processing and Archiving Centre
    - SVL = Svalbard Satellite Core Ground Station

    \<class ID\>

    Eight characters to indicate the processing system eg, O_NR_001 containing;
    - software platform (O for operational, F for reference, D for development and R for reprocessing);
    - timeliness of the processing workflow (NR for near real-time, ST for short time-critical and NT for non time-critical);
    - three letters/digits indicating the baseline collection. This represents a collection of processing baselines, encompassing relatively small changes. A significant change typically triggers a reprocessing and a new baseline collection.
        """
    
    out = {}
    # Extract the date and time from the relevant parts
    def string_pop(str, n):
        print(str)
        return str[:n].replace('_',''), str[n+1:]

    rs = product_id
    out['mission_id'], rs            = string_pop(rs, 3)
    out['data_source'], rs           = string_pop(rs, 2)
    out['process_level'], rs         = string_pop(rs, 1)
    out['data_type_id'], rs          = string_pop(rs, 6)
    out['sense_start_time'], rs      = string_pop(rs, len('yyyymmddThhmmss'))
    out['sense_stop_time'], rs       = string_pop(rs, len('yyyymmddThhmmss'))
    out['prduct_create_time'], rs    = string_pop(rs, len('yyyymmddThhmmss'))

    # <instance id>
    out['sensing_duration_sec'], rs  = string_pop(rs, 4)
    out['cycle_number_at_start'], rs = string_pop(rs, 3)
    out['orbit_number'], rs          = string_pop(rs, 3)
    out['frame_number'], rs          = string_pop(rs, 4)

    # GGG
    out['product_genreating_center'], rs  = string_pop(rs, 3)

    # <class id>
    out['software_platform'], rs  = string_pop(rs, 1)
    out['timeliness'], rs         = string_pop(rs, 2)
    out['baseline_collection'], rs          = string_pop(rs, 3)
    
    return out
    
def slstr_plot(m, band_vars, var, limits, lon="lon", lat="lat", cmap=plt.cm.RdBu_r):
    """Function to plot SLSTR data and embellish with gridlines and labels

    Args:
        m (axis):                   the axis to plot into
        band_vars (xarray Dataset): the variable containing the data
        limits (list):              min x, max x, min y, max y, vmin, vmax
        lon (str):                  the longitude variables in band_vars
        lat (str):                  the latitude variables in band_vars
        cmap (colormap):            the colormap to use in the plot

    Returns:
        if successful, returns p1, the pcolormesh plot instance.

    """
    minx, maxx, miny, maxy, vmin, vmax = limits
    p1 = m.pcolormesh(np.squeeze(band_vars[lon][miny:maxy,minx:maxx]),
                      np.squeeze(band_vars[lat][miny:maxy,minx:maxx]),
                      var,
                      transform=cartopy.crs.PlateCarree(central_longitude=0.0), 
                      cmap=cmap, zorder=1, vmin=vmin, vmax=vmax)

    # Embellish with gridlines
    g1 = m.gridlines(draw_labels = True, zorder=20, color='0.0', linestyle='--',linewidth=0.5)
    g1.xlocator = mticker.FixedLocator(np.arange(-180, 180, 5))
    g1.ylocator = mticker.FixedLocator(np.arange(-90, 90, 5))
    g1.top_labels = False
    g1.right_labels = False
    g1.xlabel_style = {'color': 'black'}
    g1.ylabel_style = {'color': 'black'}
    m.set(facecolor = "1.0")
    m.axis('off')
    
    return p1

def fix_time(nc, band_vars):
    """
    Fix the time variable in the dataset. It fails on scaling and masking somehow so we have to do this manually. 
    """

    band_vars_unscaled = xr.open_dataset(nc, decode_times=False, mask_and_scale=False,)

    scale_factor = band_vars_unscaled['sst_dtime'].attrs.get('scale_factor', 1)
    add_offset = band_vars_unscaled['sst_dtime'].attrs.get('add_offset', 0)
    fill_value = band_vars_unscaled['sst_dtime'].attrs.get('_FillValue')

    print(f'scale_factor: {scale_factor}')
    print(f'add_offset: {add_offset}')
    print(f'fill_value: {fill_value}')

    var_scaled = band_vars_unscaled['sst_dtime']
    if fill_value is not None:
        var_scaled = np.ma.masked_equal(var_scaled, fill_value)
    print(f'masked')
    # print(var_scaled)

    var_scaled = var_scaled * scale_factor + add_offset
    print(f'scaled')

    return var_scaled

def load_SAFE_directory_nc(SAFE_directory):
    """
    Load the SAFE directory and return the xarray Dataset containing the data.
    If there is only one file, it will not use dask to load the data.
    If there are multiple files, it will use dask to load the data.
    Args:
        SAFE_directory (str): The path to the SAFE directory containing the .nc files.
    Returns:
        band_vars (xarray Dataset): The xarray Dataset containing the data.
        sst_dtime (xarray DataArray): The SST dtime variable.
    """
    print(f'Loading SAFE directory: {SAFE_directory}')
    if not os.path.exists(SAFE_directory):
        raise FileNotFoundError(f"SAFE directory does not exist: {SAFE_directory}")
    if not os.path.isdir(SAFE_directory):
        raise NotADirectoryError(f"SAFE directory is not a directory: {SAFE_directory}")

    ncs = glob.glob(os.path.join(SAFE_directory,'*.nc'))
    nnc = len(ncs)

    if nnc == 1:
        print('no dask')
        band_vars = xr.open_dataset(ncs[0], )

        sst_dtime = fix_time(ncs[0], band_vars)
    else:
        band_vars = xr.open_mfdataset(glob.glob(os.path.join(SAFE_directory,'*.nc')), combine='by_coords', chunks=None,).load()
    # band_vars_raw = xr.open_mfdataset(glob.glob(os.path.join(SAFE_directory,'*.nc')), decode_times=False, combine='by_coords', chunks=None,)
    # band_vars['sst_dtime'] = band_vars_raw['sst_dtime']

    print('Data returned')
    return band_vars, sst_dtime
