import os										# For accessing AWS access environment variables
from enum import Enum							# For categorizing support image types

import boto3									# AWS S3 access

from .utils import get_s3_url_for_timestamp, \
create_resuable_reference_files, \
save_and_plot_image								# Import utility functions


# Define image types
ImageType = Enum("ImageType", ["CSM", "CMI"])

# Fill in with your access id and key if AWS CLI is not set up
aws_access_key_id = os.environ.get("AWS_ACCESS_KEY_ID")
aws_secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
client = boto3.client('s3', 
					  aws_access_key_id=aws_access_key_id,
					  aws_secret_access_key=aws_secret_access_key)


def get_cloudiness(goes, lat, lon, timestamp, bsize_degrees=2, ref_grid_resolution_km=8):
	"""
	Returns a cloudiness value between 0 and 1 as the average of the CSM output.
	:param goes str: GOES satellite number
	:param lat float: Bolide latitude coordinate
	:param lon float: Bolide longitude coordinate
	:param timestamp str: Bolide datetime timestamp
	:param bsize_degrees int (optional): Bounding box size by degrees
	:param ref_grid_resolution_km int (optional): Reference grid resolution in kilometers
	:return float: Cloudiness value
	"""

	data = get_image_from_s3(goes, lat, lon, timestamp, 
							 image_type=ImageType.CSM, 
							 bsize_degrees=bsize_degrees, 
							 ref_grid_resolution_km=ref_grid_resolution_km,
							 eyes=False)
	return data.mean()

def get_image_from_s3(goes, lat, lon, timestamp, 
		 image_type=ImageType.CSM, bsize_degrees=2, ref_grid_resolution_km=8, eyes=True, outfile=None):
	"""
	Returns a cloudiness value between 0 and 1 as the average of the CSM output.
	:param goes str: GOES satellite number
	:param lat float: Bolide latitude coordinate
	:param lon float: Bolide longitude coordinate
	:param timestamp str: Bolide datetime timestamp
	:param image_type ImageType (optional): Imagery type, either CSM or CMI
	:param bsize_degrees int (optional): Bounding box size by degrees
	:param ref_grid_resolution_km int (optional): Reference grid resolution in kilometers
	:param eyes bool (optional): Bool determining visualization parameters for viewing
	:param outfile str/None (optional): Image outfile name, default None
	:return float: Cloudiness value
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
		band_suffix = "C02" # red band
		data_key = "CMI"
	
	# Define prefix base from imagery
	prefix_base = "ABI-L2-{}".format(imagery)

	# Check reference grid resolution
	if ref_grid_resolution_km < 2:
		raise Exception("Cannot get finer resolution than 2 km.")
	elif ref_grid_resolution_km % 2 != 0:
		raise Exception("Only resolutions that are a multiple of 2 km are supported.")

	# Get S3 image url
	url = get_s3_url_for_timestamp(client, bucket, timestamp, goes, imagery, band_suffix, prefix_base)

	# Create reusable reference files for converting to lat lon
	lats_file = "g{}_lats_{}km.txt".format(goes, ref_grid_resolution_km)
	lons_file = "g{}_lons_{}km.txt".format(goes, ref_grid_resolution_km)
	if not os.path.exists(lats_file) or not os.path.exists(lons_file):
		create_resuable_reference_files(goes, ref_grid_resolution_km, lats_file, lons_file)
	
	return save_and_plot_image(goes, image_type, data_key, url, lat, lon, lats_file, lons_file, 
						bsize_degrees, ref_grid_resolution_km, eyes, outfile)

