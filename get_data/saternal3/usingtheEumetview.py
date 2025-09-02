# %% [markdown]
# <div class="row">
#   <div class="column">
#     <img src='./img/EUMETSAT-Logo.png' alt='Logo EUMETSAT' align='right' width='30%' />
#   </div>
#   <div class="column">
#     <img src='./img/EUMETView_icon_white.png' alt='Logo EUMETView' align='left' width='52%' />
#   </div>
# </div>

# %% [markdown]
# Copyright (c) 2020 EUMETSAT <br>
# License: MIT

# %% [markdown]
# <hr>

# %% [markdown]
# <a href="./index.ipynb"><< Index</a>
# <br>
# <a href="./4_Using_the_EUMETView_WFS_API.ipynb"><< Using the EUMETView WFS API</a>
# <span style="float:right;">
# <a href="./index.ipynb">Back to index >></a>

# %% [markdown]
# # Using the EUMETView WCS API
# 
# ### <font color='red'>Modified copy for CSSE satellite group</font>

# %% [markdown]
# The WFS API can be used to programatically retrieve any **coverage** of a specific product from the EUMETView service. By coverage, we mean the actual values of the pixels that make up a map, and not just the map image. A good example of a coverage products are the chlorophyll product from the Copernicus Sentinel-3A OLCI sensor and sea surface temperature product from the Copnericus Sentinel-3 SLSTR sensor. These are on the same platform, so have roughly the same coverage. More information on WMS systems can be found at https://docs.geoserver.org/latest/en/user/services/wcs/index.html.

# %% [markdown]
# ## What will this module teach you?
# 
# This module will show you how to:<br>
# 1. Obtain product coverage information from the EUMETView WCS API.
# 2. Learn how to get more details about the data.
# 3. Plot the data and create time-series for furtger analysis.

# %% [markdown]
# <hr>

# %% [markdown]
# As usual, we begin by importing the necessary libraries.
# 
# <i><b>Note:</b> we highly recommend that you have owslib version 0.20.0 or later, if you may receive SSL certificate warnings</i>
# 
# **<font color='red'>The project environment will need all these packages installed. Most should be on Conda, but eumdac is on pip</font>**

# %%



import os
import sys
import warnings
from IPython.core.display import HTML
from IPython.display import Image
from owslib.wcs import WebCoverageService
from owslib.util import Authentication
from owslib.fes import *
from time import sleep
import requests
import xml
from xml.etree import ElementTree
import netCDF4 as nc
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import datetime
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import eumdac
import ssl

import xarray as xr

# Turn off SSL certificate verification warnings
ssl._create_default_https_context = ssl._create_unverified_context
warnings.simplefilter("ignore")

os.makedirs("png", exist_ok=True)   # 在当前目录下建一个 png 文件夹（已存在就跳过）
# %% [markdown]
# Next we use our consumer key and secret to generate an access token. We use the EUMDAC Python library to generate a token, which we can later use in our requests. The <YOUR_CONSUMER_KEY> and <YOUR_CONSUMER_SECRET> are unique to each user and are essential for the authentication. To obtain them, log in to EumetView with your web browser, click on your username on the top right hand corner and then select 'API Key'. This will take you to the API key management page. You can then copy and paste these into the code cell bellow. 
# 
# **<font color='red'>I have just pasted in my personal key here, but we should update to an automatic read from file similar to play_w_sentinel3_eumetsat.ipynb</font>**

# %%
# Insert your personal key and secret into the single quotes
consumer_key = 'NuIve4rLXKqpMG6X7UoCI_8fVb8a'
consumer_secret = 'XGmZwA6bxOGH50iSbjlFibLprmUa'

# Provide the credentials (key, secret) for generating a token
credentials = (consumer_key, consumer_secret)

# Create a token object from the credentials
token = eumdac.AccessToken(credentials)

# Print the token and its expiration time
print(f"This token '{token}' expires {token.expiration}")

# Set up the authorization headers for future requests
auth_headers = {"Authorization": f"Bearer {token.access_token}"}

# %% [markdown]
# We access the WCS service using the following API end-point URL

# %%
service_url = 'https://view.eumetsat.int/geoserver/wcs?'
wcs = WebCoverageService(service_url, auth=Authentication(verify=False), version='2.0.1', timeout=120)

# %% [markdown]
# Now we have a connection to the WMS, we need to identify the products or target_layers we want. In this instance we will choose two.
# * copernicus__daily_sentinel3ab_olci_l2_chl_fullres
# * copernicus__daily_sentinel3ab_slstr_l2p_sst_fullres
# 
# **<font color='red'>These are the daily layers, which would be good to have in the library, but we need the instantaneous data!!!</font>**
# 
# <font color='red'>We will start with these daily layers and then move to the satellite pass data</font>

# %%
# target_layers = ['copernicus__daily_sentinel3ab_olci_l2_chl_fullres','copernicus__daily_sentinel3ab_slstr_l2p_sst_fullres'] # daily layers

# %% [markdown]
# <i>note: all WCS layers have a corresponding WMS layer, which in this case of <b>copernicus__sentinel3a_olci_l2_chl_fullres</b> would be <b>copernicus:sentinel3a_olci_l2_chl_fullres</b></i>. Also note that the WCS tag will change depending on the version of WCS used!

# %% [markdown]
# We also want to know what formats we can get the data in. This is service and method dependant. In this instance, we want to know what formats are available for a **getcoverage** request.

# %%
# check available output format options for layer 0: OLCI
# for iter_format_option in wcs.contents[target_layers[0]].supportedFormats:
#     print("Format option: ", iter_format_option)

# select format option
# format_option = 'application/x-netcdf4'

# %% [markdown]
# Coverage layers can be complex. To help us determine what options are available for each layer, we can launch a **DescribeCoverage** request for any layer. This gives us valuable information about the names of the axis the data is displayed on, for example. Lets describe the coverage for the Sentinel-3 OLCI chlorophyll product...

# %%
# describe the coverage
# payload = {
#     'service' : 'WCS',
#     'access_token': token,
#     'request' : 'DescribeCoverage',
#     'version' : '2.0.1',
#     'coverageID' : [target_layers[1]]
# }

# response = requests.get(service_url, params=payload, verify=False)
# tree = ElementTree.fromstring(response.content)
# ElementTree.dump(tree)

# %% [markdown]
# Now we have access to all this information we can make a get coverage request. For help in using this function we can run *help(wcs.getCoverage)*. We begin by defining spatial and time bounds for our query. 
# 
# *Note: For more information on time stamps, please follow this link: https://docs.geoserver.org/stable/en/user/services/wms/time.html#wms-time*
# 
# *Note: WCS search boxes are (lon1,lat1,lon2,lat2)*

# %%
# Define region of interest
region = (111, -25, 114, -20) # order is lon1,lat1,lon2,lat2

# # Set date and time 
# time = ('2020-10-16T11:40:00.000Z','2020-10-16T12:50:00.000')

# %% [markdown]
# Now we construct our two get coverage requests (one for each layer)...
# 
# Starting with chlorophyll....

# %%
# payload = {
#     'identifier' : [target_layers[0],],
#     'format' : 'application/x-netcdf4',
#     'crs' : 'EPSG:4326',\
#     'subsets' : [('Lat',region[1],region[3]),\
#                  ('Long',region[0],region[2]), \
#                  ('Time',time[0],time[1])],
#     'access_token': token
# }

# output = wcs.getCoverage(**payload)

# filename = './chl_snapshot.nc'
# with open(filename, 'wb') as f:
#     f.write(output.read())

# %%
# output.geturl()

# %% [markdown]
# 'https://view.eumetsat.int/geoserver/wcs/?request=GetCoverage&service=WCS&version=2.0.1&CoverageID=copernicus__sentinel3a_olci_l2_chl_fullres&subset=Lat%2835.0%2C37.0%29&subset=Long%28-5.5%2C-2.0%29&access_token=8cfe201c-a229-3b35-9f55-1a05bec1a658&format=application%2Fx-netcdf&crs=EPSG%3A4326&subset=%22Time%28%EF%BF%BD2020-06-19T09%3A00%3A00.000Z%22%22%2C%22%222020-06-19T09%3A59%3A59.999Z%22%22%29%22'

# %% [markdown]
# ...and now sea surface temperature.

# %%
# payload = {
#     'identifier' : [target_layers[1]],
#     'format' : 'application/x-netcdf4',
#     'crs' : 'EPSG:4326',\
#     'subsets' : [('Lat',region[1],region[3]),\
#                  ('Long',region[0],region[2]), \
#                  ('time',time[0],time[1])],
#     'access_token': token
# }

# output = wcs.getCoverage(**payload)

# filename = './sst_snapshot.nc'
# with open(filename, 'wb') as f:
#     f.write(output.read())

# %% [markdown]
# This data has been downloaded and written to netCDF files. This is a convenient format for working with gridded data. We can now open these files and read in the data. In this instance, we have only retrieved data for a single time step (so there is only 1 frame to plot).
# 
# **<font color='red'>Saving netCDF files using the netCDF4 package (as above) is a bit clunky. Worth updating to just save using xarray (.to_netcdf)</font>**
# 

# %%
# open the netCDF files
# nc_fid = nc.Dataset('chl_snapshot.nc')
# lon1 = nc_fid.variables['lon'][:]
# lat1 = nc_fid.variables['lat'][:]
# var1 = nc_fid.variables[target_layers[0].replace('__','_')][:] # small string adaptation to match variable names to layer names
# nc_fid.close()

# nc_fid = nc.Dataset('sst_snapshot.nc')
# lon2 = nc_fid.variables['lon'][:]
# lat2 = nc_fid.variables['lat'][:]
# # var2 = nc_fid.variables['Mosaic(' + target_layers[1].replace('__','_') + ')'][:] # small string adaptation to match variable names to layer names
# var2 = nc_fid.variables[target_layers[1].replace('__','_')][:] # small string adaptation to match variable names to layer names
# nc_fid.close()

# # %%
# ds = xr.open_dataset('chl_snapshot.nc')
# print(np.nanmin(ds['copernicus_daily_sentinel3ab_olci_l2_chl_fullres']))
# ds

# %% [markdown]
# **<font color='red'>Also write loading code in xarray (xr.open_dataset).</font>**
# 
# 
# And now we can plot this data....

# %%
# plot the CHL netCDF variables:
# fig = plt.figure(figsize=(20,10))
# ax = plt.subplot(1,2,1, projection=ccrs.PlateCarree(central_longitude=0.0))
# cmin = -2
# cmax = 1
# ticks=[10**x for x in range(cmin,cmax+1)]
# p1 = plt.pcolormesh(lon1,lat1,np.log10(np.squeeze(var1[0])),cmap='viridis', vmin=cmin, vmax=cmax)
# # add osm map and coastlines from EUMETView as background 
# ax.add_wms(wms=service_url, layers=["osmgray:dark", "backgrounds:ne_10m_coastline"])
# g1 = ax.gridlines(draw_labels = True)
# g1.xlabels_top = False
# g1.ylabels_right = False
# g1.xlabel_style = {'size': 16, 'color': 'gray'}
# g1.ylabel_style = {'size': 16, 'color': 'gray'}

# # colourbar
# cbar = plt.colorbar(p1, orientation='horizontal')
# cbar.set_ticks(np.log10(ticks))
# cbar.ax.set_xticklabels(ticks)
# cbar.set_label('Chlorophyll concentration [mg.m$^{-3}$]')

# # plot the SST netCDF variables:
# ax = plt.subplot(1,2,2, projection=ccrs.PlateCarree(central_longitude=0.0))
# p1 = plt.pcolormesh(lon2,lat2,np.squeeze(var2[0]),cmap='Spectral_r', vmin=np.nanmin(var2), vmax=np.nanmax(var2))
# # add osm map and coastlines from EUMETView as background 
# ax.add_wms(wms=service_url, layers=["osmgray:dark", "backgrounds:ne_10m_coastline"])
# g1 = ax.gridlines(draw_labels = True)
# g1.xlabels_top = False
# g1.ylabels_right = False
# g1.xlabel_style = {'size': 16, 'color': 'gray'}
# g1.ylabel_style = {'size': 16, 'color': 'gray'}

# # colourbar
# cbar = plt.colorbar(p1, orientation='horizontal')
# cbar.set_label('Sea surface temperature [K]')

# plt.show()

# %% [markdown]
# Not much to see today but the function works

# %% [markdown]
# We are going to re-launch our WCS queries for the SST product for a longer period of time. The box below sets the bounds of our enquiry.
# 
# **<font color='red'>This is important because the query returns different things when we look for longer time periods - important to test.</font>**
# 

# %%
# box area change over time
region = (111, -25, 114, -20) # order is lon1,lat1,lon2,lat2

# time = ('2020-06-10T09:00:00.000Z','2020-06-12T09:59:59.999Z')

# # %% [markdown]
# # And, exactly as before, we will query the sea surface temperature data that matches this query.

# # %%
# payload = {
#     'identifier' : [target_layers[1],],
#     'format' : 'application/x-netcdf4',
#     'crs' : 'EPSG:4326',\
#     'subsets' : [('Lat',region[1],region[3]),\
#                  ('Long',region[0],region[2]), \
#                  ('time',time[0],time[1])],
#     'access_token': token,
# }

# output = wcs.getCoverage(**payload)

# filename = './sst_timeseries.nc'
# with open(filename, 'wb') as f:
#     f.write(output.read())

# # %% [markdown]
# # As before, we will load in the netCDF file where the data has been written. We will also do a bit of tinkering with the time variable to convert it from a *seconds since...* paradigm to an actual date. We will also average each of our variable over the ROI for each time step.

# # %%
# # quick funtion to convert seconds since to dates...You can get the timebase and reference time from the netCDF file metadata
# date_convert = np.vectorize(lambda x: datetime.datetime(1970,1,1,0,0,0)+datetime.timedelta(seconds=x))


# nc_fid = nc.Dataset('sst_timeseries.nc')
# time2 = date_convert(nc_fid.variables['time'][:])
# var2 = nc_fid.variables[target_layers[1].replace('__','_')][:]
# # geometric average (grid size NOT taken into account)
# var2 = np.nanmean(np.nanmean(var2,1),1)
# nc_fid.close()

# # %% [markdown]
# # And finally, we can plot this time series data to see how the signals compare.
# # 
# # **<font color='red'>Again this nc package code is clunky. Xarray example below.</font>**
# # 

# # %%
# ds = xr.open_dataset('sst_timeseries.nc')
# print(np.nanmin(ds['copernicus_daily_sentinel3ab_slstr_l2p_sst_fullres']))
# ds

# # %% [markdown]
# # **<font color='red'>Interesting that we get 'daily' data every few hours. Must ba a 24-hour average updated regularly. If the user tries to download a month of daily data the file will be very large, we will want to warn the user</font>**
# # 

# # %%
# # plot the netCDF variables:
# fig,ax1 = plt.subplots(figsize=(20,10))
# ax2=ax1.twinx()
# ax2.plot(time2[np.isfinite(var2)], var2[np.isfinite(var2)], color='b')
# plt.ylabel('Sea surface temperature [K]', color='b')
# ax2.tick_params(axis='y', colors='b')

# plt.show()

# %% [markdown]
# **<font color='red'>The main thing we didn't do above is query the WCS service to see what downloads are available before downloading. I will search other notebooks for this, but you could look into this too.</font>**

# %% [markdown]
# # End of original notebook
# 
# #### Now we will look at getting the most recent data that is not interpolated

# %%
target_layers = ['copernicus__sentinel3a_slstr_l2p_sst_fullres', 'copernicus__sentinel3b_slstr_l2p_sst_fullres',\
                 'copernicus__sentinel3a_olci_l2_chl_fullres', 'copernicus__sentinel3b_olci_l2_chl_fullres']

time = ('2025-08-28T10:40:00.000Z','2025-08-31T23:50:00.000')

# %%
# check available output format options for layer 0: OLCI
for iter_format_option in wcs.contents[target_layers[0]].supportedFormats:
    print("Format option: ", iter_format_option)

# %%
# select format option
format_option = 'application/x-netcdf'

crs_option = 'EPSG:4326'

# %% [markdown]
# Maybe there is a request like this below to find out what data is available?

# %%
# describe the coverage
payload = {
    'service' : 'WCS',
    'access_token': token,
    'request' : 'DescribeCoverage',
    'version' : '2.0.1',
    'coverageID' : [target_layers[0]]
}

response = requests.get(service_url, params=payload, verify=False)
tree = ElementTree.fromstring(response.content)
ElementTree.dump(tree)

# %% [markdown]
# Using same box as above. Short time

# %%
payload = {
    'identifier' : [target_layers[0],],
    'format' : format_option,
    'crs' : crs_option,\
    'subsets' : [('Lat',region[1],region[3]),\
                 ('Long',region[0],region[2]), \
                 ('Time',time[0],time[1])],
    'access_token': token
}

output = wcs.getCoverage(**payload)
filename = 'sentinel3a/sst/nc/sentinela_sst.nc'
with open(filename, 'wb') as f:
    f.write(output.read())

# %%
sentinela_sst_ds = xr.open_dataset('sentinel3a/sst/nc/sentinela_sst.nc')
print(np.nanmax(sentinela_sst_ds['copernicus_sentinel3a_slstr_l2p_sst_fullres']))
sentinela_sst_ds

# %%
payload = {
    'identifier' : [target_layers[1],],
    'format' : format_option,
    'crs' : crs_option,\
    'subsets' : [('Lat',region[1],region[3]),\
                 ('Long',region[0],region[2]), \
                 ('Time',time[0],time[1])],
    'access_token': token
}

output = wcs.getCoverage(**payload)
filename = './sentinel3b/sst/nc/sentinelb_sst.nc'
with open(filename, 'wb') as f:
    f.write(output.read())

# %%
sentinelb_sst_ds = xr.open_dataset(filename)
print(np.nanmax(sentinelb_sst_ds['copernicus_sentinel3b_slstr_l2p_sst_fullres']))
sentinelb_sst_ds

# %% [markdown]
# I'm pretty sure sentinel b failed because there was no data inside our box during the request time. This will need to be handled automatically. 

# %%
payload = {
    'identifier' : [target_layers[2],],
    'format' : format_option,
    'crs' : crs_option,\
    'subsets' : [('Lat',region[1],region[3]),\
                 ('Long',region[0],region[2]), \
                 ('Time',time[0],time[1])],
    'access_token': token
}

output = wcs.getCoverage(**payload)
filename = 'sentinel3a/chl/nc/sentinela_chl.nc'
with open(filename, 'wb') as f:
    f.write(output.read())

# %%
sentinela_chl_ds = xr.open_dataset(filename)
print(np.nanmax(sentinela_chl_ds['copernicus_sentinel3a_olci_l2_chl_fullres']))
sentinela_chl_ds

# %%
payload = {
    'identifier' : [target_layers[3],],
    'format' : format_option,
    'crs' : crs_option,\
    'subsets' : [('Lat',region[1],region[3]),\
                 ('Long',region[0],region[2]), \
                 ('Time',time[0],time[1])],
    'access_token': token
}

output = wcs.getCoverage(**payload)
filename = './sentinel3b/chl/nc/sentinelb_chl.nc'
with open(filename, 'wb') as f:
    f.write(output.read())

# %%
sentinelb_chl_ds = xr.open_dataset(filename)
sentinelb_chl_ds
print(np.nanmax(sentinelb_chl_ds['copernicus_sentinel3b_olci_l2_chl_fullres']))

# %% [markdown]
# Interesting that SST failed for b but CHL succeeded. Maybe no good data for SST but some good data for CHL?

# %%
# plot the CHL netCDF variables:
fig, ax = plt.subplots(2,2, figsize=(12,12))

ds_list = [sentinela_sst_ds, None, sentinela_chl_ds, sentinelb_chl_ds]

for i, (x, ds) in enumerate(zip(ax.flatten(), ds_list)):
    if i != 1: #bad dataset return
        p1 = x.pcolormesh(ds['lon'], ds['lat'], ds.isel(time=0)[list(ds.keys())[0]], cmap='viridis')
        # x.set_title(ds.attrs['title'])
        # fig.colorbar(p1, ax=x, orientation='horizontal')

# %% [markdown]
# **We can see that most of the data is NaN**. This is fine, just need to be able to deal with it. And we probably can just delete layers that are all NaN from the archive so they don't show up as options in the plotting? But maybe we want to keep some kind of record of which layers were all NaN. Anyway, just use the basic code for now.

# %%
fig, ax = plt.subplots(3,6, figsize=(18,9))

for i, x in enumerate(ax.flatten()):
    p1 = x.pcolormesh(sentinela_chl_ds['lon'],
                      sentinela_chl_ds['lat'],
                      sentinela_chl_ds.isel(time=i)[list(sentinela_chl_ds.keys())[0]],
                      cmap='viridis')

ds = sentinela_chl_ds
var = list(ds.data_vars)[0]      # 找到变量名，比如 copernicus_sentinel3a_olci_l2_chl_fullres
nframes = ds.sizes['time']       # 有多少个时间片
ncols = 6                        # 每行放 6 张
nrows = (nframes + ncols - 1) // ncols   # 向上取整

fig, ax = plt.subplots(nrows, ncols, figsize=(3*ncols, 3*nrows))
ax = ax.flatten()

for i in range(nframes):
    im = ax[i].pcolormesh(ds['lon'], ds['lat'], ds[var].isel(time=i), cmap='viridis')
    ax[i].set_title(str(ds['time'].isel(time=i).values)[:16])

# 多出来的子图关掉坐标轴
for j in range(nframes, nrows*ncols):
    ax[j].axis('off')

plt.tight_layout(); 
# plt.show()

plt.savefig("sentinel3a/chl/png/fig_sentinela_chl.png", dpi=150)   # 存到 png 文件夹里
plt.close()
#单独绘制sentinela_chl每个时间片的代码#
ds = sentinela_chl_ds
var = list(ds.data_vars)[0]
nframes = ds.sizes['time']

save_dir = os.path.join("sentinel3a", "chl", "png")
os.makedirs(save_dir, exist_ok=True)

for i in range(nframes):
    z = ds[var].isel(time=i)
    tval = ds['time'].isel(time=i).values

    # 文件名：用 "-" 代替 ":"，保证合法
    fname = str(tval)[:16].replace(":", "-") + ".png"
    save_path = os.path.join(save_dir, fname)

    # 图标题：保持原始时间格式（带冒号）
    title_str = str(tval)[:16]

    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.pcolormesh(ds['lon'], ds['lat'], z, cmap='viridis')
    ax.set_title(title_str)
    plt.colorbar(im, ax=ax)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close(fig)

#到这结束##
# %%
import os
os.makedirs("png", exist_ok=True)

ds = sentinelb_sst_ds
var = list(ds.data_vars)[0]            # 变量名
nframes = ds.sizes['time']             # 时间片数量
ncols = 6                              # 每行最多放 6 张（可调）
nrows = (nframes + ncols - 1) // ncols # 向上取整

fig, ax = plt.subplots(nrows, ncols, figsize=(3*ncols, 3*nrows))
ax = ax.flatten() if nrows*ncols > 1 else [ax]

for i in range(nframes):
    im = ax[i].pcolormesh(ds['lon'], ds['lat'], ds[var].isel(time=i),
                          cmap='viridis')
    ax[i].set_title(str(ds['time'].isel(time=i).values)[:16])

# 把多出来的空格子关掉坐标轴
for j in range(nframes, nrows*ncols):
    ax[j].axis('off')

plt.tight_layout()
plt.savefig("sentinel3b/sst/png/fig_sentinelb_sst.png", dpi=150)
plt.close()

##单独绘制sentinelb_sst每个时间片的代码##
ds = sentinelb_sst_ds
var = list(ds.data_vars)[0]
nframes = ds.sizes['time']

# 目标目录（保持不变）
save_dir = os.path.join("sentinel3b", "sst", "png")
os.makedirs(save_dir, exist_ok=True)

for i in range(nframes):
    z    = ds[var].isel(time=i)
    tval = ds['time'].isel(time=i).values

    # 文件名：Windows 不允许 ":"，替换为 "-"
    fname = str(tval)[:16].replace(":", "-") + ".png"
    save_path = os.path.join(save_dir, fname)

    # 图标题：保留冒号
    title_str = str(tval)[:16]

    # 单张绘制并保存
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.pcolormesh(ds['lon'], ds['lat'], z, cmap='viridis')
    ax.set_title(title_str)
    plt.colorbar(im, ax=ax, orientation='vertical', fraction=0.046, pad=0.04)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close(fig)

##到这结束

##单独绘制sentinela_sst每个时间片的代码##
# -------- 1) Sentinel-3A SST --------
ds = sentinela_sst_ds
var = list(ds.data_vars)[0]
save_dir = os.path.join("sentinel3a", "sst", "png")
os.makedirs(save_dir, exist_ok=True)

for i in range(ds.sizes['time']):
    tval = ds['time'].isel(time=i).values
    fname = str(tval)[:16].replace(":", "-") + ".png"   # 文件名用 - 代替 :
    title = str(tval)[:16]                              # 标题保留 :
    out = os.path.join(save_dir, fname)

    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.pcolormesh(ds['lon'], ds['lat'], ds[var].isel(time=i), cmap='viridis')
    ax.set_title(title)
    plt.colorbar(im, ax=ax)
    plt.tight_layout()
    plt.savefig(out, dpi=150)
    plt.close(fig)
##到此结束##

##单独绘制sentinelb_chl每个时间片的代码##

# -------- 2) Sentinel-3B CHL --------
ds = sentinelb_chl_ds
var = list(ds.data_vars)[0]
save_dir = os.path.join("sentinel3b", "chl", "png")
os.makedirs(save_dir, exist_ok=True)

for i in range(ds.sizes['time']):
    tval = ds['time'].isel(time=i).values
    fname = str(tval)[:16].replace(":", "-") + ".png"
    title = str(tval)[:16]
    out = os.path.join(save_dir, fname)

    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.pcolormesh(ds['lon'], ds['lat'], ds[var].isel(time=i), cmap='viridis')
    ax.set_title(title)
    plt.colorbar(im, ax=ax)
    plt.tight_layout()
    plt.savefig(out, dpi=150)
    plt.close(fig)

##到此结束##
# %%



