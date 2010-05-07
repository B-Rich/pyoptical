#!/usr/bin/env python
#coding=utf-8

# Copyright (c) 2009,2010 Valentin Haenel
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

""" pyoptical - a pure python interface to the CRS 'OptiCAL' photometer

    @author:  Valentin Haenel <valentin.haenel@gmx.de>
    @version: 0.3-dev

    This module provides the 'OptiCAL' class and some supporting code.

"""

import serial

class OptiCAL(object):
    """ object to access the OptiCAL

        Example:

        import pyoptical
        op = pyoptical.OptiCAL('dev/dev/ttyUSB0')
        try:
            op.read_luminance()
        except pyoptical.NACKException as e:
            print e

        Notes about the com_port:
            The com_port argument for the constructor may vary depending on both
            your operating system and how you connect to the OptiCAL. This code was
            developed using a usb-to-serial adapter that contains a PL2303 chipset
            manufactured by Prolific:
            http://www.prolific.com.tw/eng/Products.asp?ID=59. The following
            sections outline how to access the OptiCAL using pyoptical and a
            usb-to-serial adapter containing the prolific chipset. We have not tried
            this code using a raw serial port, but would be very interested to hear
            from you if you do.

            Linux (Ubuntu Hardy):
                Support for the PL2303 chipset is compiled into the kernel, and the device
                is automatically recognised. You could check 'dmesg' for the
                following output:

                usb 2-1: new full speed USB device using uhci_hcd and address 4
                usb 2-1: configuration #1 chosen from 1 choice
                pl2303 2-1:1.0: pl2303 converter detected
                usb 2-1: pl2303 converter now attached to ttyUSB0

                In this case the com_port string is simply '/dev/ttyUSB0'

            Mac OSX (10.5.8 Leopard)
                Support for the PL2303 chipset is provided by the following
                open source driver: http://osx-pl2303.sourceforge.net/

                In this case the com_port string would be something along the
                lines of '/dev/tty.PL2303-xxx', for example:
                '/dev/tty.PL2303-000031FD'

            Windows (XP)
                The manufacturer of your usb-to-serial adapter should provide
                you with drivers.

                In this case the com_port string would be something like:
                'COM2', check the device manager for the number of the COM port.

            Other Operating Systems and Adapters:

                This code has two limitations, most importantly pyserial must support
                your platform. Secondly, if you wish to use a usb-to-serial
                adapter a driver for your target operating system must be
                available from the manufacturer or possibly a third party (for
                example and open source driver).

        Notes about possible exceptions:
            There are three types of exceptions that can happen:
                OptiCALException
                NACKException
                TimeoutException

            The OptiCALException is the base class for all exceptions in this
            module, and it is used as a general purpose exception to signify
            errors on the part of the programmer, do not quietly except these.

            The NACKException is raised when the OptiCAL responds with a NACK
            byte. It does this either if the command was not understood or if
            the command failed. If this happens during initialization, you may
            have to re-initialise the device. If this happens during readout it
            should be safe to try again instead of terminating the program.

            The TimeoutException is raised when no answer is received within the
            default timeout length. This might be caused by a number of issues,
            but essentially means that somehow the communication with the
            OptiCAL might be interrupted, for example because it is no longer
            connected to the computer.

        Implementation details:

            The interface is implemented according to the protocol specification in the
            OptiCAL-User-Guide Version 4, 1995 including the following amendments:
                a) To read out the ADC value, an 'L' must be sent instead of an 'R'
                b) The equations to convert from ADC to meaningful units had changed. See
                read_luminance() and read_voltage() for details.

            The full errata is available from the CSR website:

            http://support.crsltd.com/FileManagement/Download/9f5f62bcb3e64eb8934fe72afb937cb6

            The corrected versions of the conversion formulas can also be found
            in the OptiCAL.py python interface available from the CRS website,
            written by Walter F. Bischof in 2007.

            The constructor will first perform the initial calibration of the
            device as required by the protocol specification. Next it will read
            out all parameters from the eeprom and store them as private
            variables. And lastly it will put the device into the default mode.

            The initial version of the OptiCAL hardware supported two readout
            modes 'current' and 'voltage'. The device could be used to read
            luminace when in 'current' mode and 'voltage' when in voltage mode.
            Over the years there have been two revisions of the OptiCAL
            hardware, both no longer supported usage as a voltmeter, and thus
            the 'voltage' mode has become redundant. Since version 0.2 this
            interface no longer supports the 'voltage' mode, and the device will
            be put into 'current' mode at startup.

    """

    _ACK = '\x06'
    _NACK = '\x15'

    def __init__(self, com_port, timeout=5):
        """ initialise OptiCAL

            arguments:
                com_port:   name of the com_port
                timeout:    time in seconds to wait for a response

            For more information about the 'com_port' argument see
            the docstring of the class.

        """
        self._phot = serial.Serial(com_port, timeout=timeout)
        self._calibrate()
        self._read_ref_defs()
        self._read_other_defs()
        self._set_current_mode()

    def __str__(self):
        return "Optical found at : " + self._phot.port + "\n" + \
               "Product Type :     " + str(self._product_type) + "\n" \
               "Optical S/N  :     " + str(self._optical_serial_number) + "\n" \
               "Firmware version : " + str(self._firmware_version) + "\n" \
               "V_ref:             " + str(self._V_ref) + "\n" + \
               "Z_count:           " + str(self._Z_count) + "\n" + \
               "R_feed:            " + str(self._R_feed) + "\n" + \
               "R_gain:            " + str(self._R_gain) + "\n" + \
               "Probe S/N          " + str(self._probe_serial_number) + "\n" + \
               "K_cal:             " + str(self._K_cal) + "\n"

    def _send_command(self, command, description):
        """ send a single command character and read a single response (ACK/NACK)"""
        self._phot.write(command)
        ret = self._phot.read()
        _check_return(ret, description)

    def _calibrate(self):
        """ perform initial calibration

            As stated in the OptiCAL user guide, this must be done after
            powering up the device, before any readouts are performed.

        """
        self._send_command('C', "calibrate")

    def _set_current_mode(self):
        """ put the device into 'current' mode """
        self._send_command('I', "set current mode")

    def _read_eeprom_single(self, address):
        """ read contents of eeprom at single address

            arguments:
                address: an integer in the range 0<i<100

            returns:
                a byte in the range 0<i<256 as str

            note: the ACK byte is truncated
        """
        self._phot.write(chr(128+address))
        ret = self._phot.read(2)
        _check_return(ret, "reading eeprom at address %d" % address)
        # if _check_return does not raise an excpetion
        return ret[0]

    def _read_eeprom(self, start, stop):
        """ read contents of eeprom between start and stop inclusive

            arguments:
                start: an integer in the range 0<i<100
                stop: and integer in the range 0<i<100

            returns:
                a string of bytes, each in the range 0<i<255
        """
        return "".join([self._read_eeprom_single(i) for i in range(start, stop+1)])

    def _read_product_type(self):
        return _to_int(self._read_eeprom(0, 1))

    def _read_optical_serial_number(self):
        return _to_int(self._read_eeprom(2, 5))

    def _read_firmware_version(self):
        return float(_to_int(self._read_eeprom(6, 7)))/100

    def _read_probe_serial_number(self):
        return int(self._read_eeprom(80, 95))

    def _read_other_defs(self):
        """ read all parameters that do not have a ref definition """
        self._product_type = self._read_product_type()
        self._optical_serial_number = self._read_optical_serial_number()
        self._firmware_version = self._read_firmware_version()
        self._probe_serial_number = self._read_probe_serial_number()

    def _read_V_ref(self):
        """ reference voltage in microV """
        return _to_int(self._read_eeprom(16, 19))

    def _read_Z_count(self):
        """ zero error in ADC counts """
        return _to_int(self._read_eeprom(32, 35))

    def _read_R_feed(self):
        """ feedback resistor in Ohm """
        return _to_int(self._read_eeprom(48, 51))

    def _read_R_gain(self):
        """ voltage gain resistor in Ohm """
        return _to_int(self._read_eeprom(64, 67))

    def _read_K_cal(self):
        """ probe calibration in fA/cd/m**2 """
        return _to_int(self._read_eeprom(96, 99))

    def _read_ref_defs(self):
        """ read all parameters with a ref definition """
        self._V_ref = self._read_V_ref()
        self._Z_count = self._read_Z_count()
        self._R_feed = self._read_R_feed()
        self._R_gain = self._read_R_gain()
        self._K_cal = self._read_K_cal()

    def _read_adc(self):
        """ read and adjust the ADC value """
        self._phot.write('L')
        ret = self._phot.read(4)
        _check_return(ret, "reading adc value")
        # truncate the ACK
        ret = ret[:-1]
        # obtain an integer value from the bytes
        adc = _to_int(ret)
        return adc - self._Z_count - 524288

    def read_luminance(self):
        """ the luminance in cd/m**2 """
        ADC_adjust = self._read_adc()
        numerator =  (float(ADC_adjust)/524288) * self._V_ref * 1.e-6
        denominator = self._R_feed * self._K_cal * 1.e-15
        return max(0.0, numerator / denominator)

def _to_int(byte_string):
    """ convert a string of bytes(in least significant byte order) to int """
    return int(byte_string[::-1].encode('hex'), 16)

def _check_return(ret, description):
    """ check the return value of a read, raise exception if its not o.k. """
    if ret == "":
        raise TimeoutException(description)
    if OptiCAL._NACK in ret:
        raise NACKException(description)

def get_version():

    start = __doc__.find("@version")+10
    end = __doc__.find("\n\n", start)
    version = __doc__[start: end]
    return version

class OptiCALException(Exception):
    """ base exception for all OptiCAL exceptions """

class NACKException(OptiCALException):
    """ is raised when the OptiCAL sends a NACK byte to signify an error"""
    def __str__(self):
        return "OptiCAL sent a NACK while trying to: %s" % self.message

class TimeoutException(OptiCALException):
    """ is raised when the OptiCAL does not respond within the timeout limit """
    def __str__(self):
        return "OptiCAL timeout while trying to: %s" % self.message

if __name__ == "__main__":
    usage = "pyoptical [-i interval] [-n number ] [-r] com-port"
    version = "%prog: " + get_version()
    error_prefix = "pyoptical.py: error:"

    from optparse import OptionParser
    import sys
    import time
    from itertools import repeat

    parser = OptionParser(usage="\n  " + usage, version=version)

    parser.add_option("-i", "--interval",
            action = "store",
            type = "float",
            dest = "interval",
            default = 0.0,
            help = "the measurement interval in ms, default is as fast as possible")
    parser.add_option("-n", "--number",
            action = "store",
            type = "int",
            dest = "number",
            default = None,
            help = "number of measurements to make, default is endless")
    parser.add_option("-r", "--robust",
            action = "store_true",
            dest = "robust",
            default = False,
            help = "when encountering an error, try to continue ignoring as many exceptions as possible")

    opts, args = parser.parse_args()
    if len(args) != 1:
        parser.error("wrong number of arguments")
        sys.exit(-1)

    op = OptiCAL(args[0])

    # this is a hack, either it executes opts.number times, or endlessly
    for i in repeat(None) if opts.number is None else repeat(None, opts.number):
        try:
            print op.read_luminance()
            time.sleep(opts.interval/1000)
        except OptiCALException, e:
            sys.stderr.write(error_prefix + str(e) + "\n")
            if opts.robust:
                continue
            else:
                sys.exit(-1)

