installdist
-----------

:code:`installdist` is used to ease the installation of local Python packages. It will probably be most useful to developers who are working with Python packages. With a single command, it will look for the nearest **dist/** directory, identify the package with the highest version (or most recent timestamp), uninstall any pre-existing package with the same name, then install the package to the local installation. It doesn't do anything that :code:`pip` fundamentally can't, it just simplifies the workflow greatly.


Installation
============

::

  pip3 install --user installdist

The :code:`installdist` package is known to be compatible with Python 3.


Usage
=====

    usage: installdist [OPTIONS] FILES/FOLDERS

    Smartly install local Python source packages.

    optional arguments:
      -2, --pip2            install package with pip2
      -a, --auto            skip prompts for user input
      -d, --dry-run         indicate the commands to be run but do not execute
                            them
      -n, --new             install package possessing the most recent timestamp
      -p PACKAGE, --package PACKAGE
                            install package by parent directory
      -q, --quiet           suppress normal output (for use with --auto)
      -s, --system          install to system directory
      -v, --verbose         set logging level to verbose
      --version             show program's version number and exit
      -w, --wheel           install wheel package

    NOTE: By default, installdist will uninstall any pre-existing installation
    before using `pip3 install --user` to install the highest version zip or
    tarball package available.

Please note that by default, :code:`installdist` will use :code:`pip3 install --user` to install the highest version zip or tarball package available. If you'd like to use :code:`pip2`, wheel packages, the package with the most recent timestamp, or install to the system installation, use the appropriate flag.

:code:`installdist` will not make changes without prompting you for confirmation, so don't fear mistakes. To test a command, you may use the dry run flag (:code:`-d` or :code:`--dry-run`). It will simulate the command exactly, including any prompts.

To install a Python source package from the package's root directory, :code:`installdist` will look for a **dist/** directory (in the current and parent directories) and identify the package with the highest version number.

::

    installdist

To install a Python source package from the package's root directory, :code:`installdist` will look for a **dist/** directory (in the current and parent directories) and identify the package possessing the most recent timestamp.

::

    installdist --new

To install a Python source package:

::

    installdist package.tar.gz

To install a Python source package by indicating the package's parent directory:

::

    installdist -p ~/Development/project

If you are working in a *virtualenv* or wish to install to your root installation, remember to use the :code:`--system` flag:

::

    installdist -s


License
=======

Copyright (c) 2015 Six (brbsix@gmail.com).

Licensed under the GPLv3 license.
