import os									# Check files
import gc									# Clean memory for repeated plots
import requests								# Read from S3
from datetime import datetime, timedelta	# Datetime handling
from json import loads, dumps				# Loading and storing intermediate results

import numpy as np							# Scientific computing with Python
import matplotlib.pyplot as plt				# Plotting library
import cartopy.crs as ccrs					# Plot maps
from netCDF4 import Dataset					# Read / Write NetCDF4 files
from pyproj import Proj						# Cartographic projections and coordinate transformations library


def save_and_plot_image(goes, image_type, data_key, url, lat, lon, lats_file, lons_file, 
						bsize_degrees, ref_grid_resolution_km, eyes, outfile):

	# Open the GOES-R image
	image = url.split("/")[-1]
	resp = requests.get(url)
	image_file = Dataset(image, memory=resp.content)
	
	# Get the image resolution
	band_resolution_km = getattr(image_file, 'spatial_resolution')
	band_resolution_km = float(band_resolution_km[:band_resolution_km.find("km")])
	
	# Get min max lat lon
	min_lon, max_lon, min_lat, max_lat = lon - bsize_degrees, lon + bsize_degrees, lat - bsize_degrees, lat + bsize_degrees
	extent = [min_lon, min_lat, max_lon, max_lat]
	
	# Read the GOES-R lat lons as arrays (image_files created previously)
	lats = np.loadtxt(lats_file)
	lons = np.loadtxt(lons_file)

	# Calculate the lat lon pairs indexes for the desired extent
	idx_pair_1 = abs(lats-extent[1])+abs(lons-extent[0])
	max_lat_idx,min_lon_idx = np.unravel_index(idx_pair_1.argmin(),idx_pair_1.shape)
	idx_pair_2 = abs(lats-extent[3])+abs(lons-extent[2])
	min_lat_idx,max_lon_idx = np.unravel_index(idx_pair_2.argmin(),idx_pair_2.shape)
	
	# Adapt the reference indexes for the current image_file resolution
	min_lat_idx = min_lat_idx * int(ref_grid_resolution_km/band_resolution_km)
	min_lon_idx = min_lon_idx * int(ref_grid_resolution_km/band_resolution_km)
	max_lat_idx = max_lat_idx * int(ref_grid_resolution_km/band_resolution_km)
	max_lon_idx = max_lon_idx * int(ref_grid_resolution_km/band_resolution_km)
	
	# The projection x and y coordinates equals the scanning angle (in radians) multiplied by the satellite height
	sat_h = image_file.variables['goes_imager_projection'].perspective_point_height
	x = image_file.variables['x'][min_lon_idx:max_lon_idx] * sat_h
	y = image_file.variables['y'][min_lat_idx:max_lat_idx] * sat_h
	
	# Get the pixel values
	data = image_file.variables[data_key][min_lat_idx:max_lat_idx,min_lon_idx:max_lon_idx][::1,::1]
	
	# Get satellite longitude and sweep
	sat_lon = image_file.variables['goes_imager_projection'].longitude_of_projection_origin
	sat_sweep = image_file.variables['goes_imager_projection'].sweep_angle_axis
	
	# Use the Geostationary projection in cartopy
	plt.figure(figsize=(7,7))
	ax = plt.axes(projection=ccrs.Geostationary(central_longitude=sat_lon, satellite_height=sat_h))
	img_extent = (x.min(), x.max(), y.min(), y.max())
	if eyes:
		# Add visual elements
		
		# Insert Label
		target_lat = lat
		target_lon = lon
		label = "Target"
		x_offset = 0.1
		y_offset = 0
		ax.plot([target_lon], [target_lat], 'ro', markersize=5, transform=ccrs.Geodetic())
		ax.text(target_lon + x_offset , target_lat + y_offset, label, 
				fontsize=12, fontweight='bold', zorder=8, color='gold', transform=ccrs.Geodetic())

		# Get the image file date
		add_seconds = int(image_file.variables['time_bounds'][0])
		date = datetime(2000,1,1,12) + timedelta(seconds=add_seconds)
		date = date.strftime('%d %B %Y %H:%M UTC')
		
		# Add a title
		plt.title('GOES-{} {}'.format(goes, image_type.name), fontweight='bold', fontsize=10, loc='left')
		plt.title('Sub Region \n' + date, fontsize=10, loc='right')
	else:
		# Turn off axes
		ax.axis("off")

	# Plot the image
	img = ax.imshow(data, vmin=0.0, vmax=0.7, extent=img_extent, origin='upper', cmap='gray')

	# Save the image
	if outfile is None:
		outfile = '{}__{}_{}.png'.format(image[:-3], lat, lon)
		plt.savefig(outfile)

	if eyes:
		# Show the image
		plt.show()

	# Clean up
	plt.close("all")
	gc.collect()

	return data

def get_s3_url_for_timestamp(client, bucket, timestamp, goes, imagery, band_suffix, prefix_base):
	# Split timestamp into date and time
	if "T" in timestamp:
		date, time = timestamp.split("T")
	else:
		date, time = timestamp.split(" ")
	
	# Extract closet year, days, hour, and minute
	year = date.split("-")[0]
	days = (datetime.strptime(date, "%Y-%m-%d") - datetime.strptime(year, "%Y"))
	days = int(days.days + 1)
	if days < 10:
		days = "00{}".format(days)
	elif days < 100:
		days = "0{}".format(days)
	hour, minute, _ = time.split(":")
	rounded_down_minute = minute[0] + "0"

	# Format into S3 prefix
	addendum = "{year}/{days}/{hour}/OR_ABI-L2-{imagery}-M6{band_suffix}_G{goes}_s{year}{days}{hour}{minute}".format(
		year=year, days=days, hour=hour, minute=rounded_down_minute, goes=goes, imagery=imagery, band_suffix=band_suffix
	)
	prefix = "{}/{}".format(prefix_base, addendum)
	result = client.list_objects(Bucket=bucket, Prefix=prefix, Delimiter='/')
	# Check content
	keys = [i["Key"] for i in result.get("Contents", [])]
	if not keys:
		raise Exception("Could not find image for {}".format(prefix))

	# Form into url and return
	base_url = "https://noaa-goes{}.s3.amazonaws.com".format(goes)
	image = keys[0]
	url = "{}/{}".format(base_url, image)

	return url

def create_resuable_reference_files(goes, ref_grid_resolution_km, lats_file, lons_file):
	# Reference file, does not matter if image type does not match up as long as GOES satellite matches
	if goes == "16":
		image = "OR_ABI-L2-ACMF-M6_G16_s20220010000205_e20220010009513_c20220010011165.nc"
		image_url = "https://noaa-goes16.s3.amazonaws.com/ABI-L2-ACMF/2022/001/00/OR_ABI-L2-ACMF-M6_G16_s20220010000205_e20220010009513_c20220010011165.nc"
	elif goes == "17":
		image = "OR_ABI-L2-ACMF-M6_G17_s20220010000320_e20220010009386_c20220010010501.nc"
		image_url = "https://noaa-goes17.s3.amazonaws.com/ABI-L2-ACMF/2022/001/00/OR_ABI-L2-ACMF-M6_G17_s20220010000320_e20220010009386_c20220010010501.nc"
	else:
		raise Exception("GOES {} not supported".format(goes))

	resp = requests.get(image_url)
	image_file = Dataset(image, memory=resp.content)

	# Satellite height
	sat_h = image_file.variables['goes_imager_projection'].perspective_point_height
	# Satellite longitude
	sat_lon = image_file.variables['goes_imager_projection'].longitude_of_projection_origin
	# Satellite sweep
	sat_sweep = image_file.variables['goes_imager_projection'].sweep_angle_axis

	# The projection x and y coordinates equals
	# the scanning angle (in radians) multiplied by the satellite height (http://proj4.org/projections/geos.html)
	step = int(ref_grid_resolution_km/2)
	X = image_file.variables['x'][:][::step] * sat_h
	Y = image_file.variables['y'][:][::step] * sat_h
	# Map object with pyproj
	p = Proj(proj='geos', h=sat_h, lon_0=sat_lon, sweep=sat_sweep)
	# Convert map points to latitude and longitude with the magic provided by Pyproj
	XX, YY = np.meshgrid(X, Y)
	lons, lats = p(XX, YY, inverse=True)

	# Set pixels outside the globe as -9999
	mask = (lons == lons[0][0])
	lons[mask] = -9999
	lats[mask] = -9999

	# Save for reuse
	np.savetxt(lats_file, lats, fmt='%.2f')
	np.savetxt(lons_file, lons, fmt='%.2f')

