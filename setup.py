from setuptools import setup, find_packages

setup(
    name='bolides_bounding_box',
    version='0.0.0',
    author='yajucb',
    author_email='yajucb@berkely.edu',
    packages=find_packages(),
    #   url='http://pypi.python.org/pypi/PackageName/',
    license='LICENSE.txt',
    description='A package to get bounding box images from GOES satellites.',
    long_description=open('README.md').read(),
    install_requires=[
      "requests",
      "pyproj",
      "cartopy",
      "pyshp",
      "shapely",
      "boto3",
      "pandas",
      "matplotlib",
      "numpy",
      "netCDF4",
    ]
)