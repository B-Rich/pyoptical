pyoptical
=========

about
--------------------

Pure python interface to CRS OptiCAL.

dependencies
--------------------

pyserial

install
--------------------

Available in Debian as ``python-pyoptical``, to install run::

  apt-get install python-pyoptical

Installation from source::

  ./setup.py install

(may need root/admin privileges)

documentation
--------------------

Please see the docstring for the pyoptical module.

changelog
--------------------

* 0.4 - 2012-11-21

  * Fix long standing bug where some luminance values incorrectly caused an
    error because the NACK byte was present in the ADC value and not only the
    last byte, which contains the ack value was checked. Thanks to Ivan
    Prikhodko.

* 0.3 - 2010-07-26

  * Initial implementation
  * Support command line interface and module readout
  * Extensive documentation for use on all major OSs
  * Contains changes from both early alphas, 0.1. and 0.2

author
--------------------

Copyright (C) 2009-2012 Valentin Haenel <valentin.haenel@gmx.de>

copying
--------------------

License: MIT-X, see pyoptical.py for details.
