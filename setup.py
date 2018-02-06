from setuptools import setup
import cryptory



setup(name='cryptory',
      version=cryptory.__version__,
      url='https://github.com/dashee87/cryptory',
      author='David Sheehan',
      author_email='davidfsheehan87@gamil.com',
      description='Retrieve historical cryptocurrency and other related data',
      keywords='cryptory cryptos data',
      classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Topic :: Scientific/Engineering :: Visualization'
      ],
      license='MIT',
      packages=['cryptory'],
      install_requires=[
        'pandas>=0.17.0',
        'numpy>=1.10.0',
        'pytrends>=4.0.0',
        'beautifulsoup4>=4.0.0'])
