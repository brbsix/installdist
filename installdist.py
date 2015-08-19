#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""Smartly install local Python source packages"""


import logging
import os
import sys
import tarfile
import zipfile

from contextlib import contextmanager

__program__ = 'installdist'
__version__ = '0.2.0'


class Installer:
    """A pip-like wrapper for managing package un/installation."""

    def __init__(self):
        self.options = None
        self.pkgname = None
        self.pkgpath = None
        self.pkgversion = None
        self.results = {}

    def checkpip(self):
        """Configure pip and verify that the desired version is available."""

        def finder(script):
            """Raise exception upon failure to find executable."""
            try:
                from distutil.spawn import find_executable
            except ImportError:
                from shutil import which as find_executable

            if find_executable(script):
                return script
            else:
                raise FileNotFoundError("'{0}' not available".format(script))

        self.options.pipv = finder('pip2') if self.options.pip2 else finder('pip3')

        LOGGER.info("Configured to install packages with: '%s'",
                    self.options.pipv)

    # def checkpip(self):
    #     """Configure pip and verify that the desired version is available."""

    #     def finder(script):
    #         """Raise exception upon failure to find executable."""
    #         try:
    #             from distutil.spawn import find_executable
    #         except ImportError:
    #             from shutil import which as find_executable

    #         if not find_executable(script):
    #             raise FileNotFoundError("'{0}' not available".format(script))

    #     if self.options.pip2:
    #         finder('pip2')
    #         self.options.pipv = 'pip2'
    #     else:
    #         finder('pip3')
    #         self.options.pipv = 'pip3'

    #     LOGGER.info("Configured to install packages with: '%s'",
    #                 self.options.pipv)

    def configpackage(self):
        """Determine what package is to be installed and from where."""

        # convert list to string (i.e. [None] ==> None)
        self.options.target = self.options.target[0]

        pkgpath = None

        if self.options.target is not None:
            LOGGER.info("Configured to install target package: '%s'",
                        self.options.target)
            if os.path.isfile(self.options.target):
                pkgpath = self.options.target
        else:
            LOGGER.info("Configured to scan parent directory: '%s'",
                        self.options.package)
            distpath = detectdistpath(self.options.package)
            pkgpath = self.findpackage(distpath)

        if pkgpath:
            LOGGER.info("Configured pkgpath to: '%s'", pkgpath)
            return pkgpath
        else:
            LOGGER.critical("Unable to determine package to install")
            sys.exit(1)

    def confirm(self, prompt=None):
        """Request confirmation from the user."""

        if self.options.auto:
            LOGGER.info("Bypassing prompt for user input (prompt='%s')", prompt)
            return True

        rawinput = input() if prompt is None else input(prompt)

        try:
            return True if rawinput[0].lower() == 'y' else False
        except IndexError:
            return False

    def findpackage(self, distpath):
        """
        Scan files in the 'dist/' directory and return the path
        to the desired package archive.
        """

        def versionkey(pkgpath):
            """Return package version (to be used as a sort function)."""

            wrapper = str

            try:
                # attempt to use version object (able to perform comparisons)
                from distutils.version import LooseVersion as wrapper
            except ImportError:
                pass

            return wrapper(getmetafield(pkgpath, 'version'))

        import glob

        # couldn't identify dist/, assume pkg(s) are in the current directory
        if distpath is None:
            distpath = '.'

        extension = '.whl' if self.options.wheel else '.tar.gz'
        directory = os.path.join(distpath, '*' + extension)
        paths = glob.glob(directory)
        files = [f for f in paths if os.path.isfile(f) and os.access(f, os.R_OK)]

        if files:
            if self.options.newsort:
                # select the package with the most recently changed timestamp
                return max(files, key=os.path.getctime)
            else:
                # select the package with the highest version number
                return max(files, key=versionkey)

    def installpackage(self):
        """Install package archive with pip."""

        args = [self.options.pipv, 'install', '--user', self.pkgpath]

        # install to system
        if self.options.system:
            args.remove('--user')

        logmsg = "Installing %s %s (%s)", self.pkgname, self.pkgversion, self.pkgpath

        if self.options.dryrun:
            LOGGER.dryrun(*logmsg)
            LOGGER.dryrun(args)
        else:
            LOGGER.info(*logmsg)
            LOGGER.info(args)
            _execute(args)

    # def installpackage(self):
    #     """Install package archive with pip."""

    #     args = ['install', '--user', self.pkgpath]

    #     # install to system
    #     if self.options.system:
    #         args.remove('--user')

    #     logmsg = "Installing %s %s (%s)", self.pkgname, self.pkgversion, self.pkgpath

    #     if self.options.dryrun:
    #         LOGGER.dryrun(*logmsg)
    #         LOGGER.dryrun(args)
    #     else:
    #         LOGGER.info(*logmsg)
    #         LOGGER.info(args)
    #         import pip
    #         pip.main(args)

    # def installpackage(self):
    #     """Install package archive with pip."""

    #     args = ([] if self.options.system else ['--user']) + [self.pkgpath]

    #     logmsg = "Installing %s %s (%s)", self.pkgname, self.pkgversion, self.pkgpath

    #     if self.options.dryrun:
    #         LOGGER.dryrun(*logmsg)
    #         LOGGER.dryrun(args)
    #     else:
    #         LOGGER.info(*logmsg)
    #         LOGGER.info(args)
    #         from pip.commands.install import InstallCommand
    #         install = InstallCommand()
    #         install.main(args)

    def main(self, args=None):
        """Start package un/installation process."""

        self.options = _parser(args)

        level = logging.INFO if self.options.verbose else logging.WARNING
        LOGGER.setLevel(level)

        if self.options.quiet and not self.options.auto:
            LOGGER.critical("'--quiet' can only be used with '--auto'")
            sys.exit(1)
        elif self.options.quiet and self.options.dryrun:
            LOGGER.critical("'--quiet' cannot be used with '--dry-run'")
            sys.exit(1)

        manager = null if self.options.quiet else not_null

        with manager():

            self.checkpip()

            # determine the path of package that is to be (un)installed
            self.pkgpath = self.configpackage()

            # determine name and version from package metadata
            self.pkgname = getmetafield(self.pkgpath, 'name')
            self.pkgversion = getmetafield(self.pkgpath, 'version')

            if self.pkgname:
                LOGGER.info("Identified package archive metadata: %s",
                            ' '.join([self.pkgname, self.pkgversion]))
                self.promptuninstall()
            else:
                LOGGER.warning("Failed to identify package metadata")

            self.promptinstall()

    def promptinstall(self):
        """Prompt to install package archive."""

        prompt = "\n{0}\nAre you sure you'd like to install the aforementio" \
                 "ned package (y/N)? ".format(os.path.abspath(self.pkgpath))

        if self.confirm(prompt):
            self.installpackage()
        else:
            sys.exit(1)

    def promptuninstall(self):
        """Prompt to uninstall package archive."""

        self.results = self.showpackage()

        if self.results:
            LOGGER.info("Identified installed package: '%s'", self.pkgname)

            if not self.options.auto:
                print('Name:', self.results['name'])
                print('Version:', self.results['version'])
                print('Location:', self.results['location'])
                print()

            prompt = "Are you sure you'd like to uninstall {0} {1} (y/N)? " \
                     .format(self.pkgname, self.results['version'])

            if self.confirm(prompt):
                self.uninstallpackage()
            else:
                sys.exit(1)

        else:
            LOGGER.info("Failed to identify any installed package: '%s'",
                        self.pkgname)

    def showpackage(self):
        """Return a set of details for an installed package."""

        import subprocess

        awk = "awk '/^Name: / {n=$2} /^Version: / {v=$2} /^Location: / {l=" \
              "$2} END{if (n==\"\") exit 1; printf \"%s|%s|%s\", n, v, l}'"

        process = subprocess.Popen(
            '{0} show {1} | {2}'.format(self.options.pipv, self.pkgname, awk),
            executable='bash',
            shell=True,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE)

        # check for a non-zero return code
        if process.wait(timeout=5) != 0:
            return False

        info = process.stdout.read().decode().split('|')

        results = {}

        if info:
            results = {
                'name': info[0],
                'version': info[1],
                'location': info[2]
                }

        return results

    # def showpackage(self):
    #     """Return a set of details for an installed package."""

    #     from pip.commands.show import search_packages_info

    #     try:
    #         generator = search_packages_info([self.pkgname])
    #         return list(generator)[0]
    #     except:
    #         pass

    def uninstallpackage(self):
        """Uninstall package archive with pip."""

        args = [self.options.pipv, 'uninstall', self.pkgname]

        if self.options.auto:
            args.insert(0, 'echo y |')

        logmsg = "Uninstalling %s %s", self.pkgname, self.results['version']

        if self.options.dryrun:
            LOGGER.dryrun(*logmsg)
            LOGGER.dryrun(args)
        else:
            LOGGER.info(*logmsg)
            LOGGER.info(args)
            _execute(args)

    # def uninstallpackage(self):
    #     """Uninstall package archive with pip."""

    #     args = ['uninstall', self.pkgname]

    #     logmsg = "Uninstalling %s %s", self.pkgname, self.results['version']

    #     if self.options.dryrun:
    #         LOGGER.dryrun(*logmsg)
    #         LOGGER.dryrun(args)
    #     else:
    #         LOGGER.info(*logmsg)
    #         LOGGER.info(args)
    #         import pip
    #         pip.main(args)

    # def uninstallpackage(self):
    #     """Uninstall package archive with pip."""

    #     logmsg = "Uninstalling %s %s", self.pkgname, self.results['version']

    #     if self.options.dryrun:
    #         LOGGER.dryrun(*logmsg)
    #     else:
    #         LOGGER.info(*logmsg)
    #         # WARNING: can fail to identify the package to be uninstalled
    #         from pip.commands import UninstallCommand
    #         uninstall = UninstallCommand()
    #         uninstall.main([self.pkgname])


@contextmanager
def not_null():
    """Not a context manager. This is just a placeholder."""
    yield


@contextmanager
def null():
    """
    A context manager to temporarily redirect
    stdout and stderr to /dev/null.

    e.g.:

    with null():
        compute()
    """

    try:
        original_stderr = os.dup(sys.stderr.fileno())
        original_stdout = os.dup(sys.stdout.fileno())
        devnull = open(os.devnull, 'w')
        os.dup2(devnull.fileno(), sys.stderr.fileno())
        os.dup2(devnull.fileno(), sys.stdout.fileno())
        yield

    finally:
        if original_stderr is not None:
            os.dup2(original_stderr, sys.stderr.fileno())
        if original_stdout is not None:
            os.dup2(original_stdout, sys.stdout.fileno())
        if devnull is not None:
            devnull.close()


def _execute(args):
    """Execute shell commands with access to terminal."""
    os.system(' '.join(args))


def _parser(args):
    """Parse command-line options and arguments. Arguments may consist of any
    combination of directories, files, and options."""

    import argparse

    parser = argparse.ArgumentParser(
        add_help=False,
        description='Smartly install local Python source packages.',
        epilog='NOTE: By default, %(prog)s will uninstall any pre-existing '
               'installation before using `pip3 install --user` to install '
               'the highest version tarball available.',
        usage='%(prog)s [OPTIONS] FILES/FOLDERS')
    parser.add_argument(
        '-2', '--pip2',
        action='store_true',
        dest='pip2',
        help='install package with pip2')
    parser.add_argument(
        '-a', '--auto',
        action='store_true',
        dest='auto',
        help='skip prompts for user input')
    parser.add_argument(
        '-d', '--dry-run',
        action='store_true',
        dest='dryrun',
        help='indicate the commands to be run but do not execute them')
    parser.add_argument(
        '-h', '--help',
        action='help',
        help=argparse.SUPPRESS)
    parser.add_argument(
        '-n', '--new',
        action='store_true',
        dest='newsort',
        help='install package possessing the most recent timestamp')
    parser.add_argument(
        '-p', '--package',
        action='store',
        default='.',
        dest='package',
        help='install package by parent directory')
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        dest='quiet',
        help='suppress normal output (for use with --auto)')
    parser.add_argument(
        '-s', '--system',
        action='store_true',
        dest='system',
        help='install to system directory')
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        dest='verbose',
        help='set logging level to verbose')
    parser.add_argument(
        '--version',
        action='version',
        version='{0} {1}'.format(__program__, __version__))
    parser.add_argument(
        '-w', '--wheel',
        action='store_true',
        dest='wheel',
        help='install wheel package')
    parser.add_argument(
        action='append',
        dest='target',
        help=argparse.SUPPRESS,
        nargs='?')

    return parser.parse_args(args)


def detectdistpath(startpath):
    """Return the relative path to the desired 'dist/' directory."""

    searchpaths = ['.', 'dist/', '../dist/']

    for searchpath in searchpaths:
        testpath = os.path.join(startpath, searchpath) if startpath else \
                   searchpath
        basename = os.path.basename(os.path.abspath(testpath))
        if os.path.isdir(testpath) and basename == 'dist':
            return testpath


def dryrun(self, message, *args, **kwargs):
    """Create custom log level function for logging module."""
    if self.isEnabledFor(logging.DRYRUN):
        self._log(logging.DRYRUN, message, args, **kwargs)  # pylint: disable=W0212


def getmetapath(pkgpath, afo):
    """
    Return path to the metadata file within a tarfile or zipfile object.

    tarfile: PKG-INFO
    zipfile: metadata.json
    """

    if isinstance(afo, tarfile.TarFile):
        for path in afo.getnames():
            if path.endswith('/PKG-INFO'):
                return path
    elif isinstance(afo, zipfile.ZipFile):
        for path in afo.namelist():
            if path.endswith('.dist-info/metadata.json'):
                return path

    LOGGER.critical("Unable to identify metadata file for '%s'",
                    os.path.basename(pkgpath))
    sys.exit(1)


def getmetafield(pkgpath, field):
    """
    Return the value of a field from package metadata file.
    Whenever possible, version fields are returned as a version object.

    i.e. getmetafield('/path/to/archive-0.3.tar.gz', 'name') ==> 'archive'
    """

    # package is a tar archive
    if pkgpath.endswith('.tar.gz'):

        with tarfile.open(pkgpath) as tfo:
            with tfo.extractfile(getmetapath(pkgpath, tfo)) as mfo:
                metalines = mfo.read().decode().splitlines()

        for line in metalines:
            if line.startswith(field.capitalize() + ': '):
                return line.split(': ')[-1]

    # package is a wheel (zip) archive
    elif pkgpath.endswith('.whl'):

        import json

        with zipfile.ZipFile(pkgpath) as zfo:
            metadata = json.loads(zfo.read(getmetapath(pkgpath, zfo)).decode())
            try:
                return metadata[field.lower()]
            except KeyError:
                pass

    LOGGER.critical("Unable to extract field '%s' from package '%s'",
                    field, pkgpath)
    sys.exit(1)


def main():
    """Start application."""
    installer = Installer()
    installer.main()


# create custom logging level DRYRUN
logging.DRYRUN = 35
logging.addLevelName(logging.DRYRUN, 'DRYRUN')
logging.Logger.dryrun = dryrun

# configure logging formatter
LOGGER = logging.getLogger(__program__)
STREAM = logging.StreamHandler()
FORMAT = logging.Formatter('(%(name)s) %(levelname)s: %(message)s')
STREAM.setFormatter(FORMAT)
LOGGER.addHandler(STREAM)

if __name__ == '__main__':
    main()
