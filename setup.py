# -*- coding: utf-8 -*-

from setuptools import setup
from installdist import __program__
from installdist import __version__


def read(filename):
    with open(filename) as f:
        return f.read()


setup(
    name=__program__,
    version=__version__,
    author='Brian Beffa',
    author_email='brbsix@gmail.com',
    description='Smartly install python source packages',
    long_description=read('README.rst'),
    url='https://github.com/brbsix/installdist',
    license='GPLv3',
    py_modules=['installdist'],
    entry_points={
        'console_scripts': ['installdist=installdist:main'],
    },
    keywords=['development', 'package', 'pip', 'distribution', 'wheel'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.0',
        'Programming Language :: Python :: 3.1',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Utilities',
    ],
)
