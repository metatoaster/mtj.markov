from setuptools import setup, find_packages
import os

version = '0.0'

setup(name='mtj.markov',
      version=version,
      description="Markov text generator",
      long_description=open("README.rst").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.rst")).read(),
      # Get more strings from
      # http://pypi.python.org/pypi?:action=list_classifiers
      classifiers=[
        "Programming Language :: Python",
        ],
      keywords='',
      author='Tommy Yu',
      author_email='y@metatoaster.com',
      url='https://github.com/metatoaster/mtj.markov',
      license='GPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['mtj'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          # -*- Extra requirements: -*-
          'sqlalchemy',
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
