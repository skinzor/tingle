#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PyCompatLayer - Compatibility layer for Python.

It make all versions of Python behaving as the latest version of Python 3.
It will allow to add compatibility with all versions of Python without effort.
It is still under development, not all functions are supported.
"""

from __future__ import nested_scopes
import sys

__version__ = "0.0.10.dev6"
__author__ = "ale5000"
__copyright__ = "Copyright (C) 2016-2017, ale5000"
__license__ = "LGPLv3+"


class _InternalReferences(object):
    """For internal use only."""
    UsedCalledProcessError = None

    def __new__(cls, *args, **kwargs):
        raise TypeError(cls.__doc__)


class _Internal(object):
    """For internal use only."""

    def __new__(cls, *args, **kwargs):
        raise TypeError(cls.__doc__)

    class SubprocessError(Exception):
        pass

    class ExtStr(str):
        def format(format_string, *args, **kwargs):  # Largely incomplete (it only use the first value of args)
            format_string = format_string.replace("{}", "%s").replace("{0}", "%s").replace("{:", "%").replace("}", "")
            return format_string % (args[0], )

        def __format__(value, format_spec):  # Largely incomplete
            return "%"+format_spec % (value, )


def _subprocess_called_process_error(already_exist, subprocess_lib):
    if already_exist:
        class ExtCalledProcessError(subprocess_lib.CalledProcessError):
            """Raised when a process run by check_call() or check_output()
            returns a non-zero exit status."""

            def __init__(self, returncode, cmd, output=None, stderr=None):
                try:
                    super(ExtCalledProcessError, self).__init__(returncode=returncode,
                                                                cmd=cmd, output=output, stderr=stderr)
                except TypeError:
                    try:
                        super(ExtCalledProcessError, self).__init__(returncode=returncode,
                                                                    cmd=cmd, output=output)
                    except TypeError:
                        super(ExtCalledProcessError, self).__init__(returncode=returncode,
                                                                    cmd=cmd)
                        self.output = output
                    self.stdout = output
                    self.stderr = stderr

        _InternalReferences.UsedCalledProcessError = ExtCalledProcessError
    else:
        class CalledProcessError(subprocess_lib.SubprocessError):
            """Raised when a process run by check_call() or check_output()
            returns a non-zero exit status."""

            def __init__(self, returncode, cmd, output=None, stderr=None):
                subprocess_lib.SubprocessError.__init__(self, "Command '" + str(cmd) + "' returned non-zero exit status " + str(returncode))
                self.returncode = returncode
                self.cmd = cmd
                self.output = output
                self.stdout = output
                self.stderr = stderr

        _InternalReferences.UsedCalledProcessError = CalledProcessError


# API

def set_default_encoding(encoding="utf-8"):
    if sys.getdefaultencoding() != encoding:
        try:
            reload(sys)
            sys.setdefaultencoding(encoding)
        except (NameError, AttributeError):
            pass


def fix_base(fix_environ):
    """Activate the base compatibility."""
    def _is_android():
        import os

        vm_path = os.sep+"system"+os.sep+"bin"+os.sep+"dalvikvm"
        if os.path.exists(vm_path) or os.path.exists(os.sep+"system"+vm_path):
            return True
        try:
            import android
            del android  # Unused import (imported only for Android detection)
            return True
        except ImportError:
            pass
        return False

    def _fix_android_environ():
        import os

        if "LD_LIBRARY_PATH" not in os.environ:
            os.environ["LD_LIBRARY_PATH"] = ""

        lib_path = os.pathsep+"/system/lib"+os.pathsep+"/vendor/lib"
        if sys.python_bits == 64:
            lib_path = os.pathsep+"/system/lib64"+os.pathsep+"/vendor/lib64" + lib_path

        os.environ["LD_LIBRARY_PATH"] += lib_path

    if sys.platform.startswith("linux") and sys.platform != "linux-android":
        if _is_android():
            sys.platform = "linux-android"
        elif "-" not in sys.platform:
            sys.platform = "linux"

    sys.platform_codename = sys.platform
    if sys.platform_codename == "win32":
        sys.platform_codename = "win"
    elif sys.platform_codename == "linux-android":
        sys.platform_codename = "android"

    if 'maxsize' in sys.__dict__:
        if sys.maxsize > 2**32:
            sys.python_bits = 64
        else:
            sys.python_bits = 32
    else:
        import struct
        sys.python_bits = 8 * struct.calcsize("P")
        if sys.python_bits == 32:
            sys.maxsize = 2147483647
        else:
            sys.maxsize = int("9223372036854775807")

    if fix_environ and sys.platform == "linux-android":
        _fix_android_environ()


def fix_builtins(override_debug=False):
    """Activate the builtins compatibility."""
    override_dict = {}
    orig_print = None
    used_print = None

    if(__builtins__.__class__ is dict):
        builtins_dict = __builtins__
    else:
        try:
            import builtins
        except ImportError:
            import __builtin__ as builtins
        builtins_dict = builtins.__dict__

    def _deprecated(*args, **kwargs):
        """Report the fact that the called function is deprecated."""
        import traceback
        raise DeprecationWarning("the called function is deprecated => " +
                                 traceback.extract_stack(None, 2)[0][3])

    def _print_wrapper(*args, **kwargs):
        flush = kwargs.get("flush", False)
        if "flush" in kwargs:
            del kwargs["flush"]
        orig_print(*args, **kwargs)
        if flush:
            kwargs.get("file", sys.stdout).flush()

    def _print_full(*args, **kwargs):
        opt = {"sep": " ", "end": "\n", "file": sys.stdout, "flush": False}
        for key in kwargs:
            if(key in opt):
                opt[key] = kwargs[key]
            else:
                raise TypeError("'"+key+"' is an invalid keyword argument "
                                "for this function")
        opt["file"].write(opt["sep"].join(str(val) for val in args)+opt["end"])
        if opt["flush"]:
            opt["file"].flush()

    def _sorted(my_list):
        my_list = list(my_list)
        my_list.sort()
        return my_list

    def _format(value, format_spec):
        return value.__format__(format_spec)

    if builtins_dict.get(__name__, False):
        raise RuntimeError(__name__+" already loaded")

    # Exceptions
    if builtins_dict.get("BaseException") is None:
        override_dict["BaseException"] = Exception

    # basestring
    if builtins_dict.get("basestring") is None:
        if builtins_dict.get("bytes") is None:
            import types
            override_dict["basestring"] = types.StringType
        else:
            override_dict["basestring"] = (str, bytes)  # It works only when used in isinstance
    # IntType
    if getattr(int, "__str__", None) is None:
        import types
        override_dict["IntType"] = types.IntType
    else:
        override_dict["IntType"] = int  # Python >= 2.2

    if 'format' not in str.__dict__:
        override_dict["str"] = _Internal.ExtStr
    # Function 'input'
    if builtins_dict.get("raw_input") is not None:
        override_dict["input"] = builtins_dict.get("raw_input")
    override_dict["raw_input"] = _deprecated
    # Function 'print' (also aliased as print_)
    if sys.version_info >= (3, 3):
        used_print = builtins_dict.get("print")
    else:
        orig_print = builtins_dict.get("print")
        if orig_print is not None:
            used_print = _print_wrapper
        else:
            used_print = _print_full
        override_dict["print"] = used_print
    override_dict["print_"] = used_print
    # Function 'sorted'
    if builtins_dict.get("sorted") is None:
        override_dict["sorted"] = _sorted
    # Function 'format'
    if builtins_dict.get("format") is None:
        override_dict["format"] = _format

    override_dict[__name__] = True
    builtins_dict.update(override_dict)
    del override_dict


def fix_subprocess(override_debug=False, override_exception=False):
    """Activate the subprocess compatibility."""
    import subprocess

    # Exceptions
    if subprocess.__dict__.get("SubprocessError") is None:
        subprocess.SubprocessError = _Internal.SubprocessError
    if _InternalReferences.UsedCalledProcessError is None:
        if "CalledProcessError" in subprocess.__dict__:
            _subprocess_called_process_error(True, subprocess)
        else:
            _subprocess_called_process_error(False, subprocess)
            subprocess.CalledProcessError = _InternalReferences.UsedCalledProcessError

    def _check_output(*args, **kwargs):
        if "stdout" in kwargs:
            raise ValueError("stdout argument not allowed, "
                             "it will be overridden.")
        process = subprocess.Popen(stdout=subprocess.PIPE, *args, **kwargs)
        stdout_data, __ = process.communicate()
        ret_code = process.poll()
        if ret_code is None:
            raise RuntimeWarning("The process is not yet terminated.")
        if ret_code:
            cmd = kwargs.get("args")
            if cmd is None:
                cmd = args[0]
            raise _InternalReferences.UsedCalledProcessError(returncode=ret_code, cmd=cmd, output=stdout_data)
        return stdout_data

    try:
        subprocess.check_output
    except AttributeError:
        subprocess.check_output = _check_output


def fix_all(override_debug=False, override_all=False):
    """Activate the full compatibility."""
    fix_base(True)
    fix_builtins(override_debug)
    fix_subprocess(override_debug, override_all)
    return True
