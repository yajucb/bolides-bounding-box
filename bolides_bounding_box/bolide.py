import requests

from . import API_ENDPOINT_EVENT

from bolides_bounding_box.bounding_box import get_cloudiness, get_image_from_s3

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
	def cloudiness(self):
		# Returns average cloud cover around the bolide as determined by the Clear Sky Mask (CSM) algorithm 
		# https://www.goes-r.gov/products/baseline-clear-sky-mask.html
		cloudiness = []
		for glm in self.detectedBy:
			goes = glm.split("-")[-1]
			cloudiness.append(get_cloudiness(goes, self.latitude, self.longitude, self.datetime))
		return sum(cloudiness)/len(cloudiness)
	
	def get_bounding_box(self, bsize_degrees=2):
		# Get a bounding box image of the region of interest around the bolide
		for glm in self.detectedBy:
			goes = glm.split("-")[-1]
			get_image_from_s3(goes, self.latitude, self.longitude, self.datetime, bsize_degrees=bsize_degrees)