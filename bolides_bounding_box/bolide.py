import requests

from . import API_ENDPOINT_EVENT

from bolides_bounding_box.bounding_box import get_cloudiness, get_bb_image

class Bolide():
	"""Represents a bright fireball reported at https://neo-bolide.ndc.nasa.gov
	Parameters
	----------
	eventid : str
			Unique identifier of the event as used by https://neo-bolide.ndc.nasa.gov.

	"""
	def __init__(self, eventid):
		self.eventid = eventid
		self.json = self._load_json(eventid)['data'][0]
		self.nSatellites = len(self.json['attachments'])

	def _load_json(self, eventid):
		"""Returns a dictionary containing the data for the bolide."""
		url = f"{API_ENDPOINT_EVENT}/{eventid}"
		r = requests.get(url)
		return r.json()

	@property
	def detectedBy(self):
		return self.json['detectedBy'].split(",")

	@property
	def latitude(self):
		return self.json['latitude']

	@property
	def longitude(self):
		return self.json['longitude']

	@property
	def datetime(self):
		return self.json['datetime']

	@property
	def cloudiness(self, bsize_degrees=2, ref_grid_resolution_km=8, show_plot=True, outfile=None):
		"""
		Returns average cloud cover around the bolide as determined by the binary Clear Sky Mask (CSM) algorithm 
		# https://www.goes-r.gov/products/baseline-clear-sky-mask.html
		:param bsize_degree int (optional): bounding box size in degrees, default 2x2
		:param ref_grid_resolution_km int (optional): reference grid resolution in kilometers, default 8
		:param show_plot bool (optional): bool for showing plot with visual elements, default True
		:param outfile str (outfile): outfile where the bounding box image will be saved, default None which uses the eventid
		:return float: cloudiness in the bounding box between 0 and 1, where 0 is no cloud and 1 is all cloud
		"""
		cloudiness = []
		for glm in self.detectedBy:
			goes = glm.split("-")[-1]
			cloudiness.append(get_cloudiness(goes, self.latitude, self.longitude, self.datetime, 
				bsize_degrees=bsize_degrees, ref_grid_resolution_km=ref_grid_resolution_km, show_plot=show_plot, outfile=outfile))
		return sum(cloudiness)/len(cloudiness)
	
	def get_bounding_box(self, bsize_degrees=2, ref_grid_resolution_km=8, show_plot=True, outfile=None):
		"""
		Get a bounding box image of the region of interest around the bolide.
		:param bsize_degree int (optional): bounding box size in degrees, default 2x2
		:param ref_grid_resolution_km int (optional): reference grid resolution in kilometers, default 8
		:param show_plot bool (optional): bool for showing plot with visual elements, default True
		:param outfile str (outfile): outfile where the bounding box image will be saved, default None which uses the eventid
		:return None:
		"""
		for glm in self.detectedBy:
			goes = glm.split("-")[-1]
			get_bb_image(goes, self.latitude, self.longitude, self.datetime, 
				bsize_degrees=bsize_degrees, ref_grid_resolution_km=ref_grid_resolution_km, show_plot=show_plot, outfile=outfile)