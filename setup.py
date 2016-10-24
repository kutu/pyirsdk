#!python3

from setuptools import setup
from irsdk import VERSION

setup(
    name='pyirsdk',
    version=VERSION,
    description='Python 3 implementation of iRacing SDK',
    author='Mihail Latyshov',
    author_email='kutu182@gmail.com',
    url='https://github.com/kutu/pyirsdk',
    py_modules=['irsdk'],
    license='MIT',
    platforms=['win32', 'win64'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'License :: OSI Approved :: MIT License',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python :: 3.3',
        'Topic :: Utilities',
    ],
    entry_points={
        'console_scripts': ['irsdk = irsdk:main'],
    },
    install_requires=[
        'PyYAML >= 3.11',
    ],
)
