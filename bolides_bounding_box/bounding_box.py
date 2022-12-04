import os													# For accessing AWS access environment variables
from enum import Enum										# For categorizing support image types

import boto3												# AWS S3 access

from .utils import get_image_file_for_timestamp_from_s3, \
create_resuable_reference_files, get_default_outfile, \
save_and_plot_bb_image										# Import utility functions


# Define image types
ImageType = Enum("ImageType", ["CSM", "CMI"])

# Fill in with your access id and key if AWS CLI is not set up
aws_access_key_id = os.environ.get("AWS_ACCESS_KEY_ID")
aws_secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
client = boto3.client('s3', 
					  aws_access_key_id=aws_access_key_id,
					  aws_secret_access_key=aws_secret_access_key)


def get_cloudiness(goes, event_id, lat, lon, timestamp, 
	bsize_degrees=2, ref_grid_resolution_km=8, show_plot=True, outfile=None):
	"""
	Returns a cloudiness value between 0 and 1 as the average of the CSM output.
	:param goes str: GOES satellite number
	:param event_id str: bolide event id
	:param lat float: bolide latitude coordinate
	:param lon float: bolide longitude coordinate
	:param timestamp str: bolide datetime timestamp
	:param bsize_degree int (optional): bounding box size in degrees, default 2x2
	:param ref_grid_resolution_km int (optional): reference grid resolution in kilometers, default 8
	:param show_plot bool (optional): bool for showing plot with visual elements, default True
	:param outfile str (outfile): outfile where the bounding box image will be saved, default None which uses the eventid
	:return float: cloudiness value
	"""

	data = get_bb_image(goes, event_id, lat, lon, timestamp, 
							 image_type=ImageType.CSM, 
							 bsize_degrees=bsize_degrees, 
							 ref_grid_resolution_km=ref_grid_resolution_km,
							 show_plot=show_plot,
							 outfile=outfile)
	return data.mean()

def get_bb_image(goes, event_id, lat, lon, timestamp, 
		 image_type=ImageType.CSM, bsize_degrees=2, ref_grid_resolution_km=8, show_plot=True, outfile=None):
	"""
	Returns a cloudiness value between 0 and 1 as the average of the CSM output.
	:param goes str: GOES satellite number
	:param event_id str: bolide event id
	:param lat float: bolide latitude coordinate
	:param lon float: bolide longitude coordinate
	:param timestamp str: bolide datetime timestamp
	:param image_type ImageType (optional): imagery type, either CSM or CMI
	:param bsize_degree int (optional): bounding box size in degrees, default 2x2
	:param ref_grid_resolution_km int (optional): reference grid resolution in kilometers, default 8
	:param show_plot bool (optional): bool for showing plot with visual elements, default True
	:param outfile str (outfile): outfile where the bounding box image will be saved, default None which uses the eventid
	:return float: cloudiness value
	"""

	# Define bucket for GOES satellite and prefix base for imagery
	bucket = "noaa-goes{}".format(goes)

	# Determine imagery
	if image_type == ImageType.CSM:
		imagery = "ACMF"
		band_suffix = ""
		data_key = "BCM"
	elif image_type == ImageType.CMI:
		imagery = "CMIPF"
		band_suffix = "C02" # red band, can be updated to check all 16
		data_key = "CMI"
	
	# Define prefix base from imagery
	prefix_base = "ABI-L2-{}".format(imagery)

	# Check reference grid resolution
	if ref_grid_resolution_km < 2:
		raise Exception("Cannot get finer resolution than 2 km.")
	elif ref_grid_resolution_km % 2 != 0:
		raise Exception("Only resolutions that are a multiple of 2 km are supported.")

	# Get image file from S3
	image_file = get_image_file_for_timestamp_from_s3(client, bucket, timestamp, goes, imagery, band_suffix, prefix_base)

	# Create reusable reference files for converting to lat lon
	lats_file = "g{}_lats_{}km.txt".format(goes, ref_grid_resolution_km)
	lons_file = "g{}_lons_{}km.txt".format(goes, ref_grid_resolution_km)
	if not os.path.exists(lats_file) or not os.path.exists(lons_file):
		create_resuable_reference_files(goes, ref_grid_resolution_km, lats_file, lons_file)

	if outfile is None:
		outfile = get_default_outfile(goes, event_id, image_type, bsize_degrees, ref_grid_resolution_km)
	
	return save_and_plot_bb_image(goes, image_type, data_key, image_file, lat, lon, lats_file, lons_file, 
						bsize_degrees, ref_grid_resolution_km, show_plot, outfile)

