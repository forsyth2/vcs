"""
# Adapted for numpy/ma/cdms2 by convertcdms.py
# Template (P) module

    .. _list: https://docs.python.org/2/library/functions.html#list
    .. _tuple: https://docs.python.org/2/library/functions.html#tuple
    .. _dict: https://docs.python.org/2/library/stdtypes.html#mapping-types-dict
    .. _None: https://docs.python.org/2/library/constants.html?highlight=none#None
    .. _str: https://docs.python.org/2/library/functions.html?highlight=str#str
    .. _bool: https://docs.python.org/2/library/functions.html?highlight=bool#bool
    .. _float: https://docs.python.org/2/library/functions.html?highlight=float#float
    .. _int: https://docs.python.org/2/library/functions.html?highlight=float#int
    .. _long: https://docs.python.org/2/library/functions.html?highlight=float#long
    .. _file: https://docs.python.org/2/library/functions.html?highlight=open#file
"""
###############################################################################
#                                                                             #
# Module:       template (P) module                                           #
#                                                                             #
# Copyright:    2000, Regents of the University of California                 #
#               This software may not be distributed to others without        #
#               permission of the author.                                     #
#                                                                             #
# Author:       PCMDI Software Team                                           #
#               Lawrence Livermore NationalLaboratory:                        #
#               support@pcmdi.llnl.gov                                        #
#                                                                             #
# Description:  Python command wrapper for VCS's template primary object.     #
#                                                                             #
# Version:      4.0                                                           #
#                                                                             #
###############################################################################
#
#
#
from __future__ import print_function
import copy
import vcs
import numpy
from .Ptext import *  # noqa
from .Pformat import *  # noqa
from .Pxtickmarks import *  # noqa
from .Pytickmarks import *  # noqa
from .Pxlabels import *  # noqa
from .Pylabels import *  # noqa
from .Pboxeslines import *  # noqa
from .Plegend import *  # noqa
from .Pdata import *  # noqa
import inspect
import cdutil
from .projection import round_projections
from .projection import elliptical_projections
from .xmldocs import scriptdocs, listdoc
import warnings

# Following for class properties


def applyFormat(value, format):
    """
    For template object that have a 'format' associated, formats the value appropriately
    formats described at: http://pyformat.io
:Example:

    .. doctest:: template_applyFormat

        >>> a=vcs.init(bg=True)
        >>> template =vcs.gettemplate()
        >>> vcs.template.applyFormat(3.45,template.mean.format)
        '3.45'

    :param value: Input to be formatted
    :type fnm: `float`_ or `int`_ or `str`_ or `object`_

    :param format: Format to use.
    :type format: `str`_

    :return: A string with formatted representation of value
    :rtype: `str`_
    """
    # Get the format
    # if is is a key in vcs existing formats then retrieve it
    # otherwise assuming user passed an actual format
    format = vcs.elements["format"].get(format, format)
    # Create the formatter string
    formatter = "{{{}}}".format(format)
    # format the value passed in
    try:
        formatted = formatter.format(value)
    except Exception:
        warnings.warn("Could not apply format {} to: `{!r}` of type {}. Leaving unchanged".format(
            formatter, value, type(value)))
        formatted = "{}".format(value)
    return formatted


def _getgen(self, name):
    return getattr(self, "_%s" % name)


def _setgen(self, name, cls, value):
    if self.name == "default":
        raise ValueError("You cannot modify the default template")
    if not isinstance(value, cls):
        raise ValueError(
            "template attribute '%s' must be of type %s" %
            (name, cls))
    setattr(self, "_%s" % name, value)


def epsilon_gte(a, b):
    """a >= b, using floating point epsilon value."""
    float_epsilon = numpy.finfo(numpy.float32).eps
    return -float_epsilon < a - b


def epsilon_lte(a, b):
    """a <= b, using floating point epsilon value."""
    float_epsilon = numpy.finfo(numpy.float32).eps
    return float_epsilon > a - b


# read .scr file
def process_src(nm, code):

    # Takes VCS script code (string) as input and generates boxfill gm from it
    try:
        t = P(nm)
    except Exception:
        t = vcs.elements["template"][nm]
    for sub in ["File", "Function", "LogicalMask", "Transform", "name", "title", "units",
                "crdate", "crtime", "comment#1",
                "comment#2", "comment#3", "comment#4", "xname", "yname", "zname", "tname",
                "xvalue", "yvalue", "zvalue", "tvalue", "xunits",
                "yunits", "zunits", "tunits", "mean", "min", "max", "xtic#1", "xtic#2",
                "xmintic#a", "xmintic#b",
                "ytic#1", "ytic#2", "ymintic#a", "ymintic#b", "xlabel#1", "xlabel#2",
                "ylabel#1", "ylabel#2",
                "box#1", "box#2", "box#3", "box#4",
                "line#1", "line#2", "line#3", "line#4", "legend", "data"]:
        # isolate that segment
        i = code.find("%s(" % sub)
        if i == -1:
            # not set in this case
            continue
        sc = code[i + len(sub) + 1:]
        j = sc.find(")")
        sc = sc[:j]
        # name on template object
        tnm = sub.lower().replace("#", "")
        if tnm == "name":
            tnm = "dataname"
        elif tnm[-4:] == "tica":
            tnm = tnm[:-4] + "tic1"
        elif tnm[-4:] == "ticb":
            tnm = tnm[:-4] + "tic2"
        elif tnm == "transform":
            tnm = "transformation"
        for S in sc.split(","):  # all attributes are comman separated
            nm, val = S.split("=")  # nm=val
            if nm == "p":
                nm = "priority"
            elif nm == "Tl":
                nm = "line"
            elif nm == "Tt":
                nm = "texttable"
            elif nm == "To":
                nm = "textorientation"
            elif nm == "Th":
                nm = "format"
            tatt = getattr(t, tnm)
            try:
                setattr(tatt, nm, eval(val))  # int float should be ok here
            except Exception:
                try:
                    setattr(tatt, nm, val)  # strings here
                except Exception:
                    # (t.name,tnm,nm,val)
                    pass
    i = code.find("Orientation(")
    t.orientation = int(code[i + 12])


#############################################################################
#                                                                           #
# Template (P) graphics method Class.                                       #
#                                                                           #
#############################################################################
class P(vcs.bestMatch):

    """The template primary method (P) determines the location of each picture
    segment, the space to be allocated to it, and related properties relevant
    to its display.

     .. describe:: Useful Functions:

        .. code-block:: python

            # Show predefined templates
            a.show('template')
            # Show predefined text table methods
            a.show('texttable')
            # Show predefined text orientation methods
            a.show('textorientation')
            # Show predefined line methods
            a.show('line')
            # Show templates as a Python list
            a.listelements('template')
            # Updates the VCS Canvas at user's request
            a.update()

    .. describe:: Make a Canvas object to work with:

        .. code-block:: python

            # VCS Canvas constructor
            a=vcs.init()

    .. describe:: Create a new instance of template:

        .. code-block:: python

            # Two ways to create a templates:
            # Copies content of 'hovmuller' to 'new'
            temp=a.createtemplate('new','hovmuller')
            # Copies content of 'default' to 'new'
            temp=a.createtemplate('new')

    .. describe:: Modify an existing template:

        .. code-block:: python

             temp=a.gettemplate('hovmuller')
    .. pragma: skip-doctest TODO convert examples to working doctests
    """
    __slots__ = ["_name", "p_name",
                 "_orientation", "_file",
                 "_function",
                 "_logicalmask",
                 "_transformation",
                 "_source", "_dataname",
                 "_title", "_units", "_crdate",
                 "_crtime", "_comment1",
                 "_comment2", "_comment3",
                 "_comment4",
                 "_xname", "_yname", "_zname", "_tname",
                 "_xunits", "_yunits", "_zunits", "_tunits",
                 "_xvalue", "_zvalue", "_yvalue", "_tvalue",
                 "_mean", "_min", "_max", "_xtic1", "_xtic2", "_xmintic1", "_xmintic2",
                 "_ytic1", "_ytic2", "_ymintic1", "_ymintic2",
                 "_xlabel1", "_xlabel2", "_box1", "_box2", "_box3", "_box4",
                 "_ylabel1", "_ylabel2",
                 "_line1", "_line2", "_line3", "_line4",
                 "_legend", "_data", "_scaledFont"]

    def _getName(self):
        return self._name
    name = property(_getName)

    def _getOrientation(self):
        return self._orientation

    def _setOrientation(self, value):
        if self.name == "default":
            raise ValueError("You cannot change the default template")
        value = VCS_validation_functions.checkInt(self, "orientation", value)
        if value not in [0, 1]:
            raise ValueError(
                "The orientation attribute must be an integer (i.e., 0 = landscape, 1 = portrait).")
        self._orientation = value
    orientation = property(
        _getOrientation,
        _setOrientation,
        "The orientation attribute must be an integer (i.e., 0 = landscape, 1 = portrait).")

    # Initialize the template attributes.                                     #
    def __init__(self, Pic_name=None, Pic_name_src='default'):
        #                                                         #
        ###########################################################
        # Initialize the template class and its members           #
        #                                                         #
        # The getPmember function retrieves the values of the     #
        # template members in the C structure and passes back the #
        # appropriate Python Object.                              #
        ###########################################################
        #                                                         #
        if (Pic_name is None):
            raise ValueError('Must provide a template name.')
        if Pic_name_src != "default" and Pic_name_src not in vcs.elements[
                "template"]:
            raise "Invalid source template: %s" % Pic_name_src
        if isinstance(Pic_name_src, P):
            Pic_name_src = Pic_name_src.name
        if Pic_name in list(vcs.elements["template"].keys()):
            raise ValueError("Template %s already exists" % Pic_name)

        self._name = Pic_name
        self.p_name = 'P'
        # properties
        self.__class__.file = property(lambda x: _getgen(x, "file"),
                                       lambda x, v: _setgen(x, "file", Pt, v))
        self.__class__.function = property(lambda x: _getgen(x, "function"),
                                           lambda x, v: _setgen(x, "function", Pt, v))
        self.__class__.logicalmask = property(lambda x: _getgen(x, "logicalmask"),
                                              lambda x, v: _setgen(x, "logicalmask", Pt, v))
        self.__class__.transformation = property(lambda x: _getgen(x, "transformation"),
                                                 lambda x, v: _setgen(x, "transformation", Pt, v))
        self.__class__.source = property(lambda x: _getgen(x, "source"),
                                         lambda x, v: _setgen(x, "source", Pt, v))
        self.__class__.dataname = property(lambda x: _getgen(x, "dataname"),
                                           lambda x, v: _setgen(x, "dataname", Pt, v))
        self.__class__.title = property(lambda x: _getgen(x, "title"),
                                        lambda x, v: _setgen(x, "title", Pt, v))
        self.__class__.units = property(lambda x: _getgen(x, "units"),
                                        lambda x, v: _setgen(x, "units", Pt, v))
        self.__class__.crdate = property(lambda x: _getgen(x, "crdate"),
                                         lambda x, v: _setgen(x, "crdate", Pt, v))
        self.__class__.crtime = property(lambda x: _getgen(x, "crtime"),
                                         lambda x, v: _setgen(x, "crtime", Pt, v))
        self.__class__.comment1 = property(lambda x: _getgen(x, "comment1"),
                                           lambda x, v: _setgen(x, "comment1", Pt, v))
        self.__class__.comment2 = property(lambda x: _getgen(x, "comment2"),
                                           lambda x, v: _setgen(x, "comment2", Pt, v))
        self.__class__.comment3 = property(lambda x: _getgen(x, "comment3"),
                                           lambda x, v: _setgen(x, "comment3", Pt, v))
        self.__class__.comment4 = property(lambda x: _getgen(x, "comment4"),
                                           lambda x, v: _setgen(x, "comment4", Pt, v))
        self.__class__.xname = property(lambda x: _getgen(x, "xname"),
                                        lambda x, v: _setgen(x, "xname", Pt, v))
        self.__class__.yname = property(lambda x: _getgen(x, "yname"),
                                        lambda x, v: _setgen(x, "yname", Pt, v))
        self.__class__.zname = property(lambda x: _getgen(x, "zname"),
                                        lambda x, v: _setgen(x, "zname", Pt, v))
        self.__class__.tname = property(lambda x: _getgen(x, "tname"),
                                        lambda x, v: _setgen(x, "tname", Pt, v))
        self.__class__.xunits = property(lambda x: _getgen(x, "xunits"),
                                         lambda x, v: _setgen(x, "xunits", Pt, v))
        self.__class__.yunits = property(lambda x: _getgen(x, "yunits"),
                                         lambda x, v: _setgen(x, "yunits", Pt, v))
        self.__class__.zunits = property(lambda x: _getgen(x, "zunits"),
                                         lambda x, v: _setgen(x, "zunits", Pt, v))
        self.__class__.tunits = property(lambda x: _getgen(x, "tunits"),
                                         lambda x, v: _setgen(x, "tunits", Pt, v))
        self.__class__.xvalue = property(lambda x: _getgen(x, "xvalue"),
                                         lambda x, v: _setgen(x, "xvalue", Pf, v))
        self.__class__.yvalue = property(lambda x: _getgen(x, "yvalue"),
                                         lambda x, v: _setgen(x, "yvalue", Pf, v))
        self.__class__.zvalue = property(lambda x: _getgen(x, "zvalue"),
                                         lambda x, v: _setgen(x, "zvalue", Pf, v))
        self.__class__.tvalue = property(lambda x: _getgen(x, "tvalue"),
                                         lambda x, v: _setgen(x, "tvalue", Pf, v))
        self.__class__.mean = property(lambda x: _getgen(x, "mean"),
                                       lambda x, v: _setgen(x, "mean", Pf, v))
        self.__class__.min = property(lambda x: _getgen(x, "min"),
                                      lambda x, v: _setgen(x, "min", Pf, v))
        self.__class__.max = property(lambda x: _getgen(x, "max"),
                                      lambda x, v: _setgen(x, "max", Pf, v))
        self.__class__.xtic1 = property(lambda x: _getgen(x, "xtic1"),
                                        lambda x, v: _setgen(x, "xtic1", Pxt, v))
        self.__class__.xtic2 = property(lambda x: _getgen(x, "xtic2"),
                                        lambda x, v: _setgen(x, "xtic2", Pxt, v))
        self.__class__.xmintic1 = property(lambda x: _getgen(x, "xmintic1"),
                                           lambda x, v: _setgen(x, "xmintic1", Pxt, v))
        self.__class__.xmintic2 = property(lambda x: _getgen(x, "xmintic2"),
                                           lambda x, v: _setgen(x, "xmintic2", Pxt, v))
        self.__class__.ytic1 = property(lambda x: _getgen(x, "ytic1"),
                                        lambda x, v: _setgen(x, "ytic1", Pyt, v))
        self.__class__.ytic2 = property(lambda x: _getgen(x, "ytic2"),
                                        lambda x, v: _setgen(x, "ytic2", Pyt, v))
        self.__class__.ymintic1 = property(lambda x: _getgen(x, "ymintic1"),
                                           lambda x, v: _setgen(x, "ymintic1", Pyt, v))
        self.__class__.ymintic2 = property(lambda x: _getgen(x, "ymintic2"),
                                           lambda x, v: _setgen(x, "ymintic2", Pyt, v))
        self.__class__.xlabel1 = property(lambda x: _getgen(x, "xlabel1"),
                                          lambda x, v: _setgen(x, "xlabel1", Pxl, v))
        self.__class__.xlabel2 = property(lambda x: _getgen(x, "xlabel2"),
                                          lambda x, v: _setgen(x, "xlabel2", Pxl, v))
        self.__class__.ylabel1 = property(lambda x: _getgen(x, "ylabel1"),
                                          lambda x, v: _setgen(x, "ylabel1", Pyl, v))
        self.__class__.ylabel2 = property(lambda x: _getgen(x, "ylabel2"),
                                          lambda x, v: _setgen(x, "ylabel2", Pyl, v))
        self.__class__.box1 = property(lambda x: _getgen(x, "box1"),
                                       lambda x, v: _setgen(x, "box1", Pbl, v))
        self.__class__.box2 = property(lambda x: _getgen(x, "box2"),
                                       lambda x, v: _setgen(x, "box2", Pbl, v))
        self.__class__.box3 = property(lambda x: _getgen(x, "box3"),
                                       lambda x, v: _setgen(x, "box3", Pbl, v))
        self.__class__.box4 = property(lambda x: _getgen(x, "box4"),
                                       lambda x, v: _setgen(x, "box4", Pbl, v))
        self.__class__.line1 = property(lambda x: _getgen(x, "line1"),
                                        lambda x, v: _setgen(x, "line1", Pbl, v))
        self.__class__.line2 = property(lambda x: _getgen(x, "line2"),
                                        lambda x, v: _setgen(x, "line2", Pbl, v))
        self.__class__.line3 = property(lambda x: _getgen(x, "line3"),
                                        lambda x, v: _setgen(x, "line3", Pbl, v))
        self.__class__.line4 = property(lambda x: _getgen(x, "line4"),
                                        lambda x, v: _setgen(x, "line4", Pbl, v))
        self.__class__.legend = property(lambda x: _getgen(x, "legend"),
                                         lambda x, v: _setgen(x, "legend", Pls, v))
        self.__class__.data = property(lambda x: _getgen(x, "data"),
                                       lambda x, v: _setgen(x, "data", Pds, v))
        #################################################
        # The following initializes the template's TEXT #
        #################################################
        self._scaledFont = False
        if Pic_name == "default":
            self._orientation = 0
            self._file = Pt('file')
            self._function = Pt('function')
            self._logicalmask = Pt('logicalmask')
            self._transformation = Pt('transformation')
            self._source = Pt('source')
            self._dataname = Pt('dataname')
            self._title = Pt('title')
            self._units = Pt('units')
            self._crdate = Pt('crdate')
            self._crtime = Pt('crtime')
            self._comment1 = Pt('comment1')
            self._comment2 = Pt('comment2')
            self._comment3 = Pt('comment3')
            self._comment4 = Pt('comment4')
            self._xname = Pt('xname')
            self._yname = Pt('yname')
            self._zname = Pt('zname')
            self._tname = Pt('tname')
            self._xunits = Pt('xunits')
            self._yunits = Pt('yunits')
            self._zunits = Pt('zunits')
            self._tunits = Pt('tunits')
            ####################################################
        # The following initializes the template's FORMATS #
            ####################################################
            self._xvalue = Pf('xvalue')
            self._yvalue = Pf('yvalue')
            self._zvalue = Pf('zvalue')
            self._tvalue = Pf('tvalue')
            self._mean = Pf('mean')
            self._min = Pf('min')
            self._max = Pf('max')
            #########################################################
        # The following initializes the template's X-TICK MARKS #
            #########################################################
            self._xtic1 = Pxt('xtic1')
            self._xtic2 = Pxt('xtic2')
            self._xmintic1 = Pxt('xmintic1')
            self._xmintic2 = Pxt('xmintic2')
            #########################################################
        # The following initializes the template's Y-TICK MARKS #
            #########################################################
            self._ytic1 = Pyt('ytic1')
            self._ytic2 = Pyt('ytic2')
            self._ymintic1 = Pyt('ymintic1')
            self._ymintic2 = Pyt('ymintic2')
            #####################################################
        # The following initializes the template's X-LABELS #
            #####################################################
            self._xlabel1 = Pxl('xlabel1')
            self._xlabel2 = Pxl('xlabel2')
            #####################################################
        # The following initializes the template's Y-LABELS #
            #####################################################
            self._ylabel1 = Pyl('ylabel1')
            self._ylabel2 = Pyl('ylabel2')
            ############################################################
        # The following initializes the template's BOXES and LINES #
            ############################################################
            self._box1 = Pbl('box1')
            self._box2 = Pbl('box2')
            self._box3 = Pbl('box3')
            self._box4 = Pbl('box4')
            self._line1 = Pbl('line1')
            self._line2 = Pbl('line2')
            self._line3 = Pbl('line3')
            self._line4 = Pbl('line4')
            #########################################################
        # The following initializes the template's LEGEND SPACE #
            #########################################################
            self._legend = Pls('legend')
            #######################################################
        # The following initializes the template's DATA SPACE #
            #######################################################
            self._data = Pds('data')
        else:
            if isinstance(Pic_name_src, P):
                Pic_name_src = P.name
            if Pic_name_src not in list(vcs.elements["template"].keys()):
                raise ValueError(
                    "The source template '%s' does not seem to exists" %
                    Pic_name_src)
            src = vcs.elements["template"][Pic_name_src]
            self.orientation = src.orientation
            self.file = copy.copy(src.file)
            self.function = copy.copy(src.function)
            self.logicalmask = copy.copy(src.logicalmask)
            self.transformation = copy.copy(src.transformation)
            self.source = copy.copy(src.source)
            self.dataname = copy.copy(src.dataname)
            self.title = copy.copy(src.title)
            self.units = copy.copy(src.units)
            self.crdate = copy.copy(src.crdate)
            self.crtime = copy.copy(src.crtime)
            self.comment1 = copy.copy(src.comment1)
            self.comment2 = copy.copy(src.comment2)
            self.comment3 = copy.copy(src.comment3)
            self.comment4 = copy.copy(src.comment4)
            self.xname = copy.copy(src.xname)
            self.yname = copy.copy(src.yname)
            self.zname = copy.copy(src.zname)
            self.tname = copy.copy(src.tname)
            self.xunits = copy.copy(src.xunits)
            self.yunits = copy.copy(src.yunits)
            self.zunits = copy.copy(src.zunits)
            self.tunits = copy.copy(src.tunits)
            ###################################################
        # The following initializes the template's FORMATS #
            ####################################################
            self.xvalue = copy.copy(src.xvalue)
            self.yvalue = copy.copy(src.yvalue)
            self.zvalue = copy.copy(src.zvalue)
            self.tvalue = copy.copy(src.tvalue)
            self.mean = copy.copy(src.mean)
            self.min = copy.copy(src.min)
            self.max = copy.copy(src.max)
            ########################################################
        # The folowing initializes the template's X-TICK MARKS #
            ########################################################
            self.xtic1 = copy.copy(src.xtic1)
            self.xtic2 = copy.copy(src.xtic2)
            self.xmintic1 = copy.copy(src.xmintic1)
            self.xmintic2 = copy.copy(src.xmintic2)
            ########################################################
        # The folowing initializes the template's Y-TICK MARKS #
            ########################################################
            self.ytic1 = copy.copy(src.ytic1)
            self.ytic2 = copy.copy(src.ytic2)
            self.ymintic1 = copy.copy(src.ymintic1)
            self.ymintic2 = copy.copy(src.ymintic2)
            ####################################################
        # The folowing initializes the template's X-LABELS #
            ####################################################
            self.xlabel1 = copy.copy(src.xlabel1)
            self.xlabel2 = copy.copy(src.xlabel2)
            ####################################################
        # The folowing initializes the template's Y-LABELS #
            ####################################################
            self.ylabel1 = copy.copy(src.ylabel1)
            self.ylabel2 = copy.copy(src.ylabel2)
            ###########################################################
        # The folowing initializes the template's BOXES and LINES #
            ###########################################################
            self.box1 = copy.copy(src.box1)
            self.box2 = copy.copy(src.box2)
            self.box3 = copy.copy(src.box3)
            self.box4 = copy.copy(src.box4)
            self.line1 = copy.copy(src.line1)
            self.line2 = copy.copy(src.line2)
            self.line3 = copy.copy(src.line3)
            self.line4 = copy.copy(src.line4)
            ########################################################
        # The folowing initializes the template's LEGEND SPACE #
            ########################################################
            self.legend = copy.copy(src.legend)
            ######################################################
        # The folowing initializes the template's DATA SPACE #
            #######################################################
            self.data = copy.copy(src.data)

        vcs.elements["template"][Pic_name] = self

    def list(self, single=None):
        """
        %s

        :param single: String value indicating which properties to list
        :type single: str
        """
        if (self.name == '__removed_from_VCS__'):
            raise ValueError('This instance has been removed from VCS.')

        if (single is None):
            print("---------- Template (P) member " +
                  "(attribute) listings ----------")
            print("method =", self.p_name)
            print("name =", self.name)
            print("orientation =", self.orientation)
            self.file.list()
            self.function.list()
            self.logicalmask.list()
            self.transformation.list()
            self.source.list()
            self.dataname.list()
            self.title.list()
            self.units.list()
            self.crdate.list()
            self.crtime.list()
            self.comment1.list()
            self.comment2.list()
            self.comment3.list()
            self.comment4.list()
            self.xname.list()
            self.yname.list()
            self.zname.list()
            self.tname.list()
            self.xunits.list()
            self.yunits.list()
            self.zunits.list()
            self.tunits.list()
            self.xvalue.list()
            self.yvalue.list()
            self.zvalue.list()
            self.tvalue.list()
            self.mean.list()
            self.min.list()
            self.max.list()
            self.xtic1.list()
            self.xtic2.list()
            self.xmintic1.list()
            self.xmintic2.list()
            self.ytic1.list()
            self.ytic2.list()
            self.ymintic1.list()
            self.ymintic2.list()
            self.xlabel1.list()
            self.xlabel2.list()
            self.ylabel1.list()
            self.ylabel2.list()
            self.box1.list()
            self.box2.list()
            self.box3.list()
            self.box4.list()
            self.line1.list()
            self.line2.list()
            self.line3.list()
            self.line4.list()
            self.legend.list()
            self.data.list()
        elif ((single == 'text') or (single == 'Pt')):
            self.file.list()
            self.function.list()
            self.logicalmask.list()
            self.transformation.list()
            self.source.list()
            self.dataname.list()
            self.title.list()
            self.units.list()
            self.crdate.list()
            self.crtime.list()
            self.comment1.list()
            self.comment2.list()
            self.comment3.list()
            self.comment4.list()
            self.xname.list()
            self.yname.list()
            self.zname.list()
            self.tname.list()
            self.xunits.list()
            self.yunits.list()
            self.zunits.list()
            self.tunits.list()
        elif ((single == 'format') or (single == 'Pf')):
            self.xvalue.list()
            self.yvalue.list()
            self.zvalue.list()
            self.tvalue.list()
            self.mean.list()
            self.min.list()
            self.max.list()
        elif ((single == 'xtickmarks') or (single == 'Pxt')):
            self.xtic1.list()
            self.xtic2.list()
            self.xmintic1.list()
            self.xmintic2.list()
        elif ((single == 'ytickmarks') or (single == 'Pyt')):
            self.ytic1.list()
            self.ytic2.list()
            self.ymintic1.list()
            self.ymintic2.list()
        elif ((single == 'xlabels') or (single == 'Pxl')):
            self.xlabel1.list()
            self.xlabel2.list()
        elif ((single == 'ylabels') or (single == 'Pyl')):
            self.ylabel1.list()
            self.ylabel2.list()
        elif ((single == 'boxeslines') or (single == 'Pbl')):
            self.box1.list()
            self.box2.list()
            self.box3.list()
            self.box4.list()
            self.line1.list()
            self.line2.list()
            self.line3.list()
            self.line4.list()
        elif ((single == 'legend') or (single == 'Pls')):
            self.legend.list()
        elif ((single == 'data') or (single == 'Pds')):
            self.data.list()
        elif (single == 'file'):
            self.file.list()
        elif (single == 'function'):
            self.function.list()
        elif (single == 'logicalmask'):
            self.logicalmask.list()
        elif (single == 'transformation'):
            self.transformation.list()
        elif (single == 'source'):
            self.source.list()
        elif (single == 'name'):
            self.name.list()
        elif (single == 'title'):
            self.title.list()
        elif (single == 'units'):
            self.units.list()
        elif (single == 'crdate'):
            self.crdate.list()
        elif (single == 'crtime'):
            self.crtime.list()
        elif (single == 'comment1'):
            self.comment1.list()
        elif (single == 'comment2'):
            self.comment2.list()
        elif (single == 'comment3'):
            self.comment3.list()
        elif (single == 'comment4'):
            self.comment4.list()
        elif (single == 'xname'):
            self.xname.list()
        elif (single == 'yname'):
            self.yname.list()
        elif (single == 'zname'):
            self.zname.list()
        elif (single == 'tname'):
            self.tname.list()
        elif (single == 'xunits'):
            self.xunits.list()
        elif (single == 'yunits'):
            self.yunits.list()
        elif (single == 'zunits'):
            self.zunits.list()
        elif (single == 'tunits'):
            self.tunits.list()
        elif (single == 'xvalue'):
            self.xvalue.list()
        elif (single == 'yvalue'):
            self.yvalue.list()
        elif (single == 'zvalue'):
            self.zvalue.list()
        elif (single == 'tvalue'):
            self.tvalue.list()
        elif (single == 'mean'):
            self.mean.list()
        elif (single == 'min'):
            self.min.list()
        elif (single == 'max'):
            self.max.list()
        elif (single == 'xtic1'):
            self.xtic1.list()
        elif (single == 'xtic2'):
            self.xtic2.list()
        elif (single == 'xmintic1'):
            self.xmintic1.list()
        elif (single == 'xmintic2'):
            self.xmintic2.list()
        elif (single == 'ytic1'):
            self.ytic1.list()
        elif (single == 'ytic2'):
            self.ytic2.list()
        elif (single == 'ymintic1'):
            self.ymintic1.list()
        elif (single == 'ymintic2'):
            self.ymintic2.list()
        elif (single == 'xlabel1'):
            self.xlabel1.list()
        elif (single == 'xlabel2'):
            self.xlabel2.list()
        elif (single == 'ylabel1'):
            self.ylabel1.list()
        elif (single == 'ylabel2'):
            self.ylabel2.list()
        elif (single == 'box1'):
            self.box1.list()
        elif (single == 'box2'):
            self.box2.list()
        elif (single == 'box3'):
            self.box3.list()
        elif (single == 'box4'):
            self.box4.list()
        elif (single == 'line1'):
            self.line1.list()
        elif (single == 'line2'):
            self.line2.list()
        elif (single == 'line3'):
            self.line3.list()
        elif (single == 'line4'):
            self.line4.list()
        elif (single == 'legend'):
            self.legend.list()
        elif (single == 'data'):
            self.data.list()
    list.__doc__ = list.__doc__ % (listdoc.format(name="template", parent=""))

    ###########################################################################
    #                                                                         #
    # Script out template object in VCS to a file.                            #
    #                                                                         #
    ###########################################################################
    def script(self, script_filename=None, mode=None):
        if (script_filename is None):
            raise ValueError(
                'Error - Must provide an output script file name.')

        if (mode is None):
            mode = 'a'
        elif (mode not in ('w', 'a')):
            raise ValueError(
                'Error - Mode can only be "w" for replace or "a" for append.')

        # By default, save file in json
        scr_type = script_filename.split(".")
        if len(scr_type) == 1 or len(scr_type[-1]) > 5:
            scr_type = "json"
            if script_filename != "initial.attributes":
                script_filename += ".json"
        else:
            scr_type = scr_type[-1]
        if scr_type == '.scr':
            raise vcs.VCSDeprecationWarning("scr script are no longer generated")
        elif scr_type == "py":
            mode = mode + '+'
            py_type = script_filename[
                len(script_filename) -
                3:len(script_filename)]
            if (py_type != '.py'):
                script_filename = script_filename + '.py'

            # Write to file
            fp = open(script_filename, mode)
            if (fp.tell() == 0):  # Must be a new file, so include below
                fp.write("#####################################\n")
                fp.write("#                                 #\n")
                fp.write("# Import and Initialize VCS     #\n")
                fp.write("#                             #\n")
                fp.write("#############################\n")
                fp.write("import vcs\n")
                fp.write("v=vcs.init()\n\n")

            unique_name = '__P__' + self.name
            fp.write(
                "#----------Template (P) member "
                "(attribute) listings ----------\n")
            fp.write("p_list=v.listelements('template')\n")
            fp.write("if ('%s' in p_list):\n" % self.name)
            fp.write(
                "   %s = v.gettemplate('%s')\n" %
                (unique_name, self.name))
            fp.write("else:\n")
            fp.write(
                "   %s = v.createtemplate('%s')\n" %
                (unique_name, self.name))
            fp.write("orientation = '%d'\n" % self.orientation)
        # Write out the TEXT template
            j = 0
            a = [
                self.file,
                self.function,
                self.logicalmask,
                self.transformation,
                self.source,
                self.dataname,
                self.title,
                self.units,
                self.crdate,
                self.crtime,
                self.comment1,
                self.comment2,
                self.comment3,
                self.comment4,
                self.xname,
                self.yname,
                self.zname,
                self.tname,
                self.xunits,
                self.yunits,
                self.zunits,
                self.tunits]
            for i in ('file', 'function', 'logicalmask', 'transformation',
                      'source', 'dataname', 'title', 'units', 'crdate', 'crtime',
                      'comment1', 'comment2', 'comment3', 'comment4', 'xname',
                      'yname', 'zname', 'tname', 'xunits', 'yunits', 'zunits', 'tunits'):
                fp.write("# member = %s\n" % i)
                fp.write(
                    "%s.%s.priority = %g\n" %
                    (unique_name, i, a[j].priority))
                fp.write("%s.%s.x = %g\n" % (unique_name, i, a[j].x))
                fp.write("%s.%s.y = %g\n" % (unique_name, i, a[j].y))
                fp.write(
                    "%s.%s.texttable = '%s'\n" %
                    (unique_name, i, a[j].texttable))
                fp.write(
                    "%s.%s.textorientation = '%s'\n\n" %
                    (unique_name, i, a[j].textorientation))
                j = j + 1

        # Write out the FORMAT template
            j = 0
            a = [
                self.xvalue,
                self.yvalue,
                self.zvalue,
                self.tvalue,
                self.mean,
                self.min,
                self.max]
            for i in (
                    'xvalue', 'yvalue', 'zvalue',
                    'tvalue', 'mean', 'min', 'max'):
                fp.write("# member = %s\n" % i)
                fp.write(
                    "%s.%s.priority = %g\n" %
                    (unique_name, i, a[j].priority))
                fp.write("%s.%s.x = %g\n" % (unique_name, i, a[j].x))
                fp.write("%s.%s.y = %g\n" % (unique_name, i, a[j].y))
                fp.write(
                    "%s.%s.texttable = '%s'\n" %
                    (unique_name, i, a[j].format))
                fp.write(
                    "%s.%s.texttable = '%s'\n" %
                    (unique_name, i, a[j].texttable))
                fp.write(
                    "%s.%s.textorientation = '%s'\n\n" %
                    (unique_name, i, a[j].textorientation))
                j = j + 1

        # Write out the X-TICK template
            j = 0
            a = [self.xtic1, self.xtic2, self.xmintic1, self.xmintic2]
            for i in ('xtic1', 'xtic2', 'xmintic1', 'xmintic2'):
                fp.write("# member = %s\n" % i)
                fp.write(
                    "%s.%s.priority = %g\n" %
                    (unique_name, i, a[j].priority))
                fp.write("%s.%s.y1 = %g\n" % (unique_name, i, a[j].y1))
                fp.write("%s.%s.y2 = %g\n" % (unique_name, i, a[j].y2))
                fp.write("%s.%s.line = '%s'\n\n" % (unique_name, i, a[j].line))
                j = j + 1

        # Write out the Y-TICK template
            j = 0
            a = [self.ytic1, self.ytic2, self.ymintic1, self.ymintic2]
            for i in ('ytic1', 'ytic2', 'ymintic1', 'ymintic2'):
                fp.write("# member = %s\n" % i)
                fp.write(
                    "%s.%s.priority = %g\n" %
                    (unique_name, i, a[j].priority))
                fp.write("%s.%s.x1 = %g\n" % (unique_name, i, a[j].x1))
                fp.write("%s.%s.x2 = %g\n" % (unique_name, i, a[j].x2))
                fp.write("%s.%s.line = '%s'\n\n" % (unique_name, i, a[j].line))
                j = j + 1

        # Write out the X-LABELS template
            j = 0
            a = [self.xlabel1, self.xlabel2]
            for i in ('xlabel1', 'xlabel2'):
                fp.write("# member = %s\n" % i)
                fp.write(
                    "%s.%s.priority = %g\n" %
                    (unique_name, i, a[j].priority))
                fp.write("%s.%s.y = %g\n" % (unique_name, i, a[j].y))
                fp.write(
                    "%s.%s.texttable = '%s'\n" %
                    (unique_name, i, a[j].texttable))
                fp.write(
                    "%s.%s.textorientation = '%s'\n\n" %
                    (unique_name, i, a[j].textorientation))
                j = j + 1

        # Write out the Y-LABELS template
            j = 0
            a = [self.ylabel1, self.ylabel2]
            for i in ('ylabel1', 'ylabel2'):
                fp.write("# member = %s\n" % i)
                fp.write(
                    "%s.%s.priority = %g\n" %
                    (unique_name, i, a[j].priority))
                fp.write("%s.%s.x = %g\n" % (unique_name, i, a[j].x))
                fp.write(
                    "%s.%s.texttable = '%s'\n" %
                    (unique_name, i, a[j].texttable))
                fp.write(
                    "%s.%s.textorientation = '%s'\n\n" %
                    (unique_name, i, a[j].textorientation))
                j = j + 1

        # Write out the BOXES and LINES template
            j = 0
            a = [
                self.box1,
                self.box2,
                self.box1,
                self.box2,
                self.line1,
                self.line2,
                self.line3,
                self.line4]
            for i in ('box1', 'box2', 'box3', 'box4',
                      'line1', 'line2', 'line3', 'line4'):
                fp.write("# member = %s\n" % i)
                fp.write(
                    "%s.%s.priority = %g\n" %
                    (unique_name, i, a[j].priority))
                fp.write("%s.%s.x1 = %g\n" % (unique_name, i, a[j].x1))
                fp.write("%s.%s.y1 = %g\n" % (unique_name, i, a[j].y1))
                fp.write("%s.%s.x2 = %g\n" % (unique_name, i, a[j].x2))
                fp.write("%s.%s.y2 = %g\n" % (unique_name, i, a[j].y2))
                fp.write("%s.%s.line = '%s'\n\n" % (unique_name, i, a[j].line))
                j = j + 1

        # Write out the LEGEND SPACE template
            fp.write("# member = %s\n" % 'legend')
            fp.write(
                "%s.legend.priority = %g\n" %
                (unique_name, self.legend.priority))
            fp.write("%s.legend.x1 = %g\n" % (unique_name, self.legend.x1))
            fp.write("%s.legend.y1 = %g\n" % (unique_name, self.legend.y1))
            fp.write("%s.legend.x2 = %g\n" % (unique_name, self.legend.x2))
            fp.write("%s.legend.y2 = %g\n" % (unique_name, self.legend.y2))
            fp.write(
                "%s.legend.line = '%s'\n" %
                (unique_name, self.legend.line))
            fp.write(
                "%s.legend.texttable = '%s'\n" %
                (unique_name, self.legend.texttable))
            fp.write(
                "%s.legend.textorientation = '%s'\n\n" %
                (unique_name, self.legend.textorientation))

        # Write out the DATA SPACE template
            fp.write("# member = %s\n" % 'data')
            fp.write(
                "%s.data.priority = %g\n" %
                (unique_name, self.data.priority))
            fp.write("%s.data.x1 = %g\n" % (unique_name, self.data.x1))
            fp.write("%s.data.y1 = %g\n" % (unique_name, self.data.y1))
            fp.write("%s.data.x2 = %g\n" % (unique_name, self.data.x2))
            fp.write("%s.data.y2 = %g\n\n" % (unique_name, self.data.y2))
        else:
            # Json type
            mode += "+"
            f = open(script_filename, mode)
            vcs.utils.dumpToJson(self, f)
            f.close()
    script.__doc__ = scriptdocs['template']

    # Adding the drawing functionnality to plot all these attributes on the
    # Canvas
    def drawTicks(self, slab, gm, x, axis, number,
                  vp, wc, bg=False, X=None, Y=None, mintic=False, **kargs):
        """Draws the ticks for the axis x number number
        using the label passed by the graphic  method
        vp and wc are from the actual canvas, they have
        been reset when they get here...

        .. pragma: skip-doctest TODO add example/doctest
        """

        kargs["donotstoredisplay"] = True
        if X is None:
            X = slab.getAxis(-1)
        if Y is None:
            Y = slab.getAxis(-2)
        displays = []
        dx = wc[1] - wc[0]
        dy = wc[3] - wc[2]
        dx = dx / (vp[1] - vp[0])
        dy = dy / (vp[3] - vp[2])
        # get the actual labels
        if mintic is False:
            loc = copy.copy(getattr(gm, axis + 'ticlabels' + number))
        else:
            loc = copy.copy(getattr(gm, axis + 'mtics' + number))
        # Are they set or do we need to it ?
        if (loc is None or loc == '*'):
            # well i guess we have to do it !
            if axis == 'x':
                x1 = wc[0]
                x2 = wc[1]
            else:
                x1 = wc[2]
                x2 = wc[3]
            loc = vcs.mkscale(x1, x2)
            loc = vcs.mklabels(loc)
            if number == '2':
                for t in list(loc.keys()):
                    loc[t] = ''
        if isinstance(loc, str):
            loc = copy.copy(vcs.elements["list"].get(loc, {}))
        # Make sure the label passed are not outside the world coordinates
        dw1 = 1.E20
        dw2 = 1.E20

        if axis == 'x':
            dw1, dw2 = wc[0], wc[1]
        else:
            dw1, dw2 = wc[2], wc[3]
        for k in list(loc.keys()):
            if dw2 > dw1:
                if not(dw1 <= k <= dw2):
                    del(loc[k])
            else:
                if not (dw1 >= k >= dw2):
                    del(loc[k])
        # The ticks
        if mintic is False:
            obj = getattr(self, axis + 'tic' + number)
        else:
            obj = getattr(self, axis + 'mintic' + number)
        # the following to make sure we have a unique name,
        # i put them together assuming it would be faster
        ticks = x.createline(source=obj.line)
        ticks.projection = gm.projection
        ticks.priority = obj.priority
        if mintic is False:
            # the labels
            objlabl = getattr(self, axis + 'label' + number)
            tt = x.createtext(
                Tt_source=objlabl.texttable,
                To_source=objlabl.textorientation)
            tt.projection = gm.projection
            tt.priority = objlabl.priority
        if vcs.elements["projection"][gm.projection].type != "linear":
            ticks.viewport = vp
            ticks.worldcoordinate = wc
            if mintic is False:
                tt.worldcoordinate = wc
                if axis == "y":
                    tt.viewport = vp
                    # TODO: Transform axes names through geographic projections
                    # In that case the if goes and only the statement stays
                    if ("ratio_autot_viewport" not in kargs):
                        tt.viewport[0] = objlabl.x
                    if vcs.elements["projection"][
                            tt.projection].type in round_projections:
                        tt.priority = 0
                else:
                    if vcs.elements["projection"][
                            tt.projection].type in round_projections:
                        xmn, xmx = vcs.minmax(self.data.x1, self.data.x2)
                        ymn, ymx = vcs.minmax(self.data.y1, self.data.y2)
                        xwiden = .02
                        ywiden = .02
                        xmn -= xwiden
                        xmx += xwiden
                        ymn -= ywiden
                        ymx += ywiden
                        vp = [
                            max(0., xmn), min(xmx, 1.), max(0, ymn), min(ymx, 1.)]
                        tt.viewport = vp
                        pass
                    else:
                        tt.viewport = vp
                        # TODO: Transform axes names through geographic projections
                        # In that case the if goes and only the statement stays
                        if ("ratio_autot_viewport" not in kargs):
                            tt.viewport[2] = objlabl.y

        # initialize the list of values
        tstring = []
        xs = []
        ys = []
        tys = []
        txs = []
        loc2 = loc
        if mintic is False:
            loc = getattr(gm, axis + 'ticlabels' + number)
        else:
            loc = getattr(gm, axis + "mtics" + number)
        if loc == '*' or loc is None:
            loc = loc2
        if isinstance(loc, str):
            loc = vcs.elements["list"].get(loc, {})
        # set the x/y/text values
        xmn, xmx = vcs.minmax(wc[0], wc[1])
        ymn, ymx = vcs.minmax(wc[2], wc[3])
        for l_tmp in list(loc.keys()):
            if axis == 'x':
                if xmn <= l_tmp <= xmx:
                    if vcs.elements["projection"][
                            gm.projection].type == "linear":
                        xs.append(
                            [(l_tmp - wc[0]) / dx +
                                vp[0], (l_tmp - wc[0]) / dx +
                                vp[0]])
                        ys.append([obj.y1, obj.y2])
                        if mintic is False:
                            txs.append((l_tmp - wc[0]) / dx + vp[0])
                            tys.append(objlabl.y)
                    elif vcs.elements["projection"][gm.projection].type in elliptical_projections:
                        pass
                    else:
                        xs.append([l_tmp, l_tmp])
                        end = wc[
                            2] + (wc[3] - wc[2]) *\
                            (obj.y2 - obj.y1) /\
                            (self.data._y2 - self._data.y1)
                        ys.append([wc[2], end])
                        if mintic is False:
                            txs.append(l_tmp)
                            tys.append(wc[3])
                    if mintic is False:
                        tstring.append(loc[l_tmp])
            elif axis == 'y':
                if ymn <= l_tmp <= ymx:
                    if vcs.elements["projection"][
                            gm.projection].type == "linear":
                        ys.append(
                            [(l_tmp - wc[2]) / dy +
                                vp[2], (l_tmp - wc[2]) / dy + vp[2]])
                        xs.append([obj.x1, obj.x2])
                        if mintic is False:
                            tys.append((l_tmp - wc[2]) / dy + vp[2])
                            txs.append(objlabl.x)
                    else:
                        ys.append([l_tmp, l_tmp])
                        end = wc[
                            0] + (wc[1] - wc[0]) *\
                            (obj._x2 - obj._x1) /\
                            (self._data._x2 - self._data.x1)
                        if vcs.elements["projection"][
                            gm.projection].type != "linear" and\
                                end < -180.:
                            end = wc[0]
                        xs.append([wc[0], end])
                        if mintic is False:
                            tys.append(l_tmp)
                            txs.append(wc[0])
                    if mintic is False:
                        tstring.append(loc[l_tmp])
        if mintic is False and txs != []:
            tt.string = tstring
            tt.x = txs
            tt.y = tys
            displays.append(x.text(tt, bg=bg, ratio="none", **kargs))
        if xs != []:
            ticks._x = xs
            ticks._y = ys
            displays.append(x.line(ticks, bg=bg, **kargs))

        del(vcs.elements["line"][ticks.name])
        if mintic is False:
            sp = tt.name.split(":::")
            del(vcs.elements["texttable"][sp[0]])
            del(vcs.elements["textorientation"][sp[1]])
            del(vcs.elements["textcombined"][tt.name])
        return displays

    def blank(self, attribute=None):
        """This function turns off elements of a template object.

        :param attribute: String or list, indicating the elements of a template
            which should be turned off. If attribute is left blank, or is None,
            all elements of the template will be turned off.
        :type attribute: `None`_ or  `str`_ or `list`_

        .. pragma: skip-doctest TODO add example/doctest
        """
        if attribute is None:
            attribute = list(self.__slots__)
            props = []
            for attr in dir(self.__class__):
                if isinstance(getattr(self.__class__, attr), property):
                    props.append(attr)
            attribute += props
        elif isinstance(attribute, str):
            attribute = [attribute, ]
        elif not isinstance(attribute, (list, tuple)):
            raise Exception("template.blank function argument "
                            "must be None, string or list")
        for a in attribute:
            try:
                elt = getattr(self, a)
                if hasattr(elt, "priority"):
                    elt.priority = 0
            except Exception:
                pass

    def reset(self, sub_name, v1, v2, ov1=None, ov2=None):
        """This function resets all the attributes having a
        sub-attribute with the specified name.

        .. note::

            Respect how far from original position you are
            i.e. if you move to x1,x2 from old_x1, old_x2
            if your current x1 value is not == to old_x1_value,
            then respect how far from it you were

        Example:

            .. doctest:: template_reset

                >>> t=vcs.createtemplate('t_reset') # inherits from 'default'
                >>> data, data2 = t.data.x1, t.data.x2
                >>> t.reset('x',0.15,0.5,data,data2) # Set x1 to 0.15, x2 to 0.5

        :param sub_name: String indicating the name of the sub-attribute to be reset.
            For example, sub_name='x' would cause the x1 ans x2 attributes to be set.
        :type sub_name: str

        :param v1: Float value to used to set the sub_name1 attribute.
        :type v1: float

        :param v2: Float value used to set the sub_name2 attribute.
        :type v2: float

        :param ov1: Float value of the old sub-name1 attribute value.
            Used to compute an offset ratio.
        :type ov1: float

        :param ov2: Float value of the old sub-name1 attribute value.
            Used to compute an offset ratio.
        :type ov2: float
        """

        Attr = dir(self)
        attr = []
        for a in Attr:
            if a[0] != "_":
                attr.append(a)
        # computes the ratio
        if ov1 is not None:
            odv = ov2 - ov1
            ratio = (v2 - v1) / odv
        else:
            ratio = 1.
        for a in attr:
            v = getattr(self, a)
            try:
                subattr = list(v.__slots__)
                props = []
                for attr in dir(v.__class__):
                    if isinstance(getattr(v.__class__, attr), property):
                        props.append(attr)
                subattr += props
                delta = 0.
                if sub_name + '1' in subattr:
                    ov = getattr(v, sub_name + '1')
                    if ov1 is not None:
                        delta = (ov - ov1) * ratio
                    setattr(v, sub_name + '1', min(1, max(0, v1 + delta)))
                delta = 0.
                if sub_name + '2' in subattr:
                    ov = getattr(v, sub_name + '2')
                    if ov2 is not None:
                        delta = (ov - ov2) * ratio
                    setattr(v, sub_name + '2', min(1, max(0, v2 + delta)))
                delta = 0.
                if sub_name in subattr:
                    ov = getattr(v, sub_name)
                    if ov1 is not None:
                        delta = (ov - ov1) * ratio
                    setattr(v, sub_name, min(1, max(0, v1 + delta)))
                    if a[-1] == '2':
                        ov = getattr(v, sub_name + '2')
                        if ov2 is not None:
                            delta = (ov - ov2) * ratio
                        setattr(v, sub_name, min(1, max(0, v2 + delta)))
            except Exception:
                pass

    def move(self, p, axis):
        """Move a template by p% along the axis 'x' or 'y'.
        Positive values of p mean movement toward right/top
        Negative values of p mean movement toward left/bottom
        The reference point is t.data.x1/y1

        :Example:

            .. doctest:: template_move

                >>> t=vcs.createtemplate('t_move') # inherits default template
                >>> t.move(0.2,'x') # Move everything right by 20%
                >>> t.move(0.2,'y') # Move everything up by 20%

        :param p: Float indicating the percentage by which the template should
            move. i.e. 0.2 = 20%.
        :type p: float

        :param axis: The axis on which the template will move.
            One of ['x', 'y'].
        :type axis: str
        """
        if axis not in ['x', 'y']:
            raise Exception('Error you can move the template only the x or y axis')
        # p/=100.
        ov1 = getattr(self.data, axis + '1')
        ov2 = getattr(self.data, axis + '2')
        v1 = ov1 + p
        v2 = ov2 + p
        self.reset(axis, v1, v2, ov1, ov2)

    def moveto(self, x, y):
        """Move a template to point (x,y), adjusting all attributes so data.x1 = x, and data.y1 = y.

        :Example:

            .. doctest:: template_moveto

                >>> t=vcs.createtemplate('t_move2') # inherits default template
                >>> t.moveto(0.2, 0.2) # Move template so x1 and y1 are 0.2

        :param x: Float representing the new coordinate of the template's
            data.x1 attribute.
        :type x: float

        :param y: Float representing the new coordinate of the template's
            data.y1 attribute.
        :type y: float
        """
        # p/=100.
        ov1 = getattr(self.data, 'x1')
        ov2 = getattr(self.data, 'x2')
        v1 = x
        v2 = (ov2 - ov1) + x
        self.reset('x', v1, v2, ov1, ov2)
        ov1 = getattr(self.data, 'y1')
        ov2 = getattr(self.data, 'y2')
        v1 = y
        v2 = (ov2 - ov1) + y
        self.reset('y', v1, v2, ov1, ov2)

    def scale(self, scale, axis='xy', font=-1):
        """Scale a template along the axis 'x' or 'y' by scale
        Values of scale greater than 1. mean increase.
        The reference point is the template's x1 and y1 data.

        :Example:

            .. doctest:: template_scale

                >>> t=vcs.createtemplate('t_scale') # inherits default template
                >>> t.scale(0.5) # Halves the template size
                >>> t.scale(1.2) # Increases size by 20%
                >>> t.scale(2,'x') # Double the x axis

        :param scale: Float representing the factor by which to scale the template.
        :type scale: float

        :param axis: One of ['x', 'y', 'xy']. Represents the axis/axes along which the template should be scaled.
        :type axis: str

        :param font: Integer flag indicating what should be done with the template's fonts. One of [-1, 0, 1].
            0: means do not scale the fonts. 1: means scale the fonts.
            -1: means do not scale the fonts unless axis='xy'
        :type font: int

        """
        if axis not in ['x', 'y', 'xy']:
            raise Exception('Error you can move the template only the x or y axis')
        # p/=100.
        if axis == 'xy':
            axis = ['x', 'y']
        else:
            axis = [axis, ]
        for ax in axis:
            ov1 = getattr(self.data, ax + '1')
            ov2 = getattr(self.data, ax + '2')
            v1 = ov1
            v2 = (ov2 - ov1) * scale + v1
            self.reset(ax, v1, v2, ov1, ov2)
        if font == 1 or (font == -1 and axis == ['x', 'y']):
            self.scalefont(scale)

    def scalefont(self, scale):
        """Scales the template font by scale.

        :Example:

            .. doctest:: template_scalefont

                >>> t=vcs.createtemplate('t_scfnt') # inherits default template
                >>> t.scalefont(0.5) # reduces the fonts size by 2

        :param scale: Float representing the factor by which to scale the template's font size.
        :type scale: float
        """
        props = []
        for attr in dir(self.__class__):
            if isinstance(getattr(self.__class__, attr), property):
                props.append(attr)
        try:
            attr = list(vars(self).keys())
        except Exception:
            attr = self.__slots__
            attr = list(attr) + props

        if len(attr) == 0:
            attr = list(self.__slots__) + props

        for a in attr:
            if a[0] == "_":
                continue
            try:
                v = getattr(self, a)
                to = getattr(v, 'textorientation')
                if self._scaledFont is False:  # first time let's copy it
                    to = vcs.createtextorientation(source=to)
                    to.height = to.height * scale
                setattr(v, 'textorientation', to)
            except Exception:
                pass
        self._scaledFont = True

    def drawLinesAndMarkersLegend(self, canvas,
                                  linecolors, linetypes, linewidths,
                                  markercolors, markertypes, markersizes,
                                  strings, scratched=None, stringscolors=None,
                                  stacking="horizontal", bg=False, render=True,
                                  smallestfontsize=None, backgroundcolor=None):
        """Draws a legend with line/marker/text inside a template legend box.
        Auto adjusts text size to make it fit inside the box.
        Auto arranges the elements to fill the box nicely.

        :Example:

            .. doctest:: template_drawLinesAndMarkersLegend

                >>> x = vcs.init()
                >>> t = vcs.createtemplate()
                >>> l_colors=["red","blue","green"]
                >>> l_types=["solid","dash","dot"]
                >>> l_widths=[1,4,8]
                >>> m_colors=["blue","green","red"]
                >>> m_types=["cross","square","dot"]
                >>> m_sizes=[3,4,5]
                >>> strings=["sample A","type B","thing C"]
                >>> scratch=[True,False,True]
                >>> t.drawLinesAndMarkersLegend(x, l_colors, l_types, l_widths,
                ...     m_colors, m_types, m_sizes, strings, scratch)
                >>> x.png("sample")

        :param canvas: a VCS canvas object onto which to draw the legend
        :type canvas: vcs.Canvas.Canvas

        :param linecolors: A list containing the colors of each line to draw.
            Colors are represented as either an int from 0-255, an rgba tuple,
            or a string color name.
        :type linecolors: `list`_

        :param linetypes: A list containing the type of each line to draw.
            Line types are represented as either integers or strings.
            See :py:class:`vcs.line.Tl` for more information.
        :type linetypes: `list`_

        :param linewidths: A list containing floats each representing the
            width of each line.
        :type linewidths: `list`_

        :param markercolors: A list of the markers colors to draw.
            Colors are represented as either an int from 0-255, an rgba tuple,
            or a string color name.
        :type markercolors: `list`_

        :param markertypes: A list of the marker types to draw.
            Marker types are represented as either integers or strings.
            See :py:class:`vcs.marker.Tm` for more information.
        :type markertypes: `list`_

        :param markersizes: A list of floats representing marker sizes.
        :type markersizes: `list`_

        :param strings: A list of strings to draw next to each line/marker.
        :type strings: `list`_

        :param scratched: A list indicating which strings should be "scratched"
            off in the template.

            To "scratch" a string, the corresponding location in the scratched
            list must contain either True or the line type to use for the
            scratch. A value of False at a given index will leave the
            corresponding index of strings untouched.

            Size of the scratched list must be equal to the size of the strings
            list.

            Scratch color will match that of text.

            If scratched is None, or is not provided, no strings will be
            scratched.
        :type scratched: `None`_ or `list`_

        :param stringscolors: A list of the strings colors to draw.
            Colors are represented as either an int from 0-255, an rgba tuple,
            or a string color name.
        :type stringscolors: `list`_

        :param stacking: Prefered direction to stack element ('horizontal' or 'vertical')
        :type stringscolors: `string`_

        :param bg: Boolean value indicating whether or not to draw in the
            background. Defaults to False.
        :type bg: bool

        :param render: Boolean value indicating whether or not to render.
            Defaults to True.
        :type render: bool

        :param smallestfontsize: Integer value indicating the smallest font size we can use for rendering
            None means no limit, 0 means use original size. Downscaling will still be used by algorigthm
            to try to fit everything in the legend box.
        :type smallestfintsize: `int`_

        :param backgroundcolor: A list indicating the background color of the legended box.
            Colors are represented as either an int from 0-255, an rgba tuple,
            or a string color name.
        :type backgroundcolor: `list`_
        """
        return vcs.utils.drawLinesAndMarkersLegend(canvas,
                                                   self.legend,
                                                   linecolors, linetypes, linewidths,
                                                   markercolors, markertypes, markersizes,
                                                   strings, scratched, stringscolors, stacking, bg,
                                                   render, smallestfontsize, backgroundcolor)

    def drawAttributes(self, x, slab, gm, bg=False, **kargs):
        """Draws attributes of slab onto a canvas

        :Example:

            .. doctest:: templates_drawAttributes

                >>> a=vcs.init()
                >>> import cdms2 # We need cdms2 to create a slab
                >>> f = cdms2.open(vcs.sample_data+'/clt.nc') # open data file
                >>> s = f('clt') # use the data file to create a slab
                >>> t=a.gettemplate()
                >>> b=a.getboxfill() # boxfill gm
                >>> t.drawAttributes(a,s,b) # shows attributes of s on canvas
                [...]

        :param x: vcs canvas onto which attributes will be drawn
        :type x: vcs.Canvas.Canvas

        :param slab: slab to get attributes from
        :type slab: cdms2.tvariable.TransientVariable or numpy.ndarray
        """
        displays = []
        # figures out the min and max and set them as atributes...
        smn, smx = vcs.minmax(slab)

        attributes = ['file', 'function', 'logicalmask', 'transformation',
                      'source', 'id', 'title', 'units', 'crdate', 'crtime',
                      'comment1', 'comment2', 'comment3', 'comment4',
                      'zname', 'tname', 'zunits', 'tunits',
                      'xvalue', 'yvalue', 'zvalue',
                      'tvalue', 'mean', 'min', 'max', 'xname', 'yname', ]

        if isinstance(gm, vcs.taylor.Gtd):
            attributes = attributes[:-5]

        # loop through various section of the template object
        for s in attributes:
            if hasattr(slab, s):
                if s == 'id':
                    sub = self.dataname
                else:
                    sub = getattr(self, s)
                tt = x.createtext(
                    None,
                    sub.texttable,
                    None,
                    sub.textorientation)

                # Now for the min/max/mean add the name in front
                kargs["donotstoredisplay"] = False
                if s == 'min':
                    fmt = self.min.format
                    if fmt == "default":  # backward compatibility
                        fmt = ":g"
                    tt.string = 'Min {}'.format(applyFormat(smn, fmt))
                elif s == 'max':
                    fmt = self.max.format
                    if fmt == "default":  # backward compatibility
                        fmt = ":g"
                    tt.string = 'Max {}'.format(applyFormat(smx, fmt))
                elif s == 'mean':
                    fmt = self.mean.format
                    if fmt == "default":  # backward compatibility
                        fmt = ":.4g"
                    if not inspect.ismethod(getattr(slab, 'mean')):
                        meanstring = getattr(slab, s)
                    else:
                        try:
                            tmp = slab(squeeze=1)
                            meanstring = float(cdutil.averager(tmp,
                                                               axis=" ".join(["(%s)" %
                                                                              S for S in tmp.getAxisIds()])))

                        except Exception:
                            try:
                                meanstring = slab.mean()
                            except Exception:
                                meanstring = slab.filled()
                    tt.string = "Mean {}".format(applyFormat(meanstring, fmt))
                else:
                    if hasattr(sub, "format"):
                        tt.string = applyFormat(getattr(slab, s), sub.format)
                    else:
                        tt.string = str(getattr(slab, s))
                    kargs["donotstoredisplay"] = False
                tt.x = [sub.x]
                tt.y = [sub.y]
                tt.priority = sub.priority
                # this is text such as variable name, min/max
                # that does not have to follow ratio=atot
                dp = x.text(tt, bg=bg, **kargs)
                if dp is not None:
                    if s != "id":
                        dp.backend["vtk_backend_template_attribute"] = s
                    else:
                        dp.backend[
                            "vtk_backend_template_attribute"] = "dataname"
                    displays.append(dp)
                sp = tt.name.split(":::")
                if kargs.get("donotstoredisplay", True):
                    del(vcs.elements["texttable"][sp[0]])
                    del(vcs.elements["textorientation"][sp[1]])
                    del(vcs.elements["textcombined"][tt.name])
        return displays

    def plot(self, x, slab, gm, bg=False, min=None,
             max=None, X=None, Y=None, **kargs):
        """This plots the template stuff on the Canvas.
        It needs a slab and a graphic method.

        .. pragma: skip-doctest TODO add example/doctest
        """

        displays = []
        kargs["donotstoredisplay"] = True
        kargs["render"] = False
        # now remembers the viewport and worldcoordinates in order to reset
        # them later
        vp = x._viewport
        wc = x._worldcoordinate
        # m=x.mode
        # and resets everything to [0,1]
        x._viewport = [0, 1, 0, 1]
        x._worldcoordinate = [0, 1, 0, 1]
        # x.mode=0 # this should disable the replot but it doesn't work....

        displays += self.drawAttributes(x, slab, gm, bg=bg, **kargs)

        kargs["donotstoredisplay"] = True
        if not isinstance(gm, vcs.taylor.Gtd):
            nms = ["x", "y", "z", "t"]
            for i, ax in enumerate(slab.getAxisList()[-2:][::-1] +
                                   [kargs.get("zaxis", None), kargs.get("taxis", None)]):
                if (hasattr(gm, "projection") and
                        vcs.elements["projection"][gm.projection].type
                        in round_projections) or ax is None:
                    continue
                for att in ["name", "units", "value"]:
                    nm = nms[i] + att
                    sub = getattr(self, nm)
                    tt = x.createtext(
                        None,
                        sub.texttable,
                        None,
                        sub.textorientation)
                    if att == "name":
                        if i == 0 and gm.g_name == "G1d":
                            if gm.flip or hasattr(slab, "_yname"):
                                tt.string = [slab.id]
                            else:
                                tt.string = [ax.id]
                        elif i == 1 and gm.g_name == "G1d":
                            if hasattr(slab, "_yname"):
                                tt.string = [slab._yname]
                            else:
                                tt.string = [ax.id]
                        else:
                            tt.string = [ax.id]
                    elif att == "units":
                        tt.string = [getattr(ax, "units", "")]
                    tt.x = [sub.x, ]
                    tt.y = [sub.y, ]
                    tt.priority = sub._priority
                    # This is the name of the axis. It should be transformed
                    # through geographic projection but it is not at the moment
                    displays.append(x.text(tt, bg=bg, **kargs))
                    sp = tt.name.split(":::")
                    del(vcs.elements["texttable"][sp[0]])
                    del(vcs.elements["textorientation"][sp[1]])
                    del(vcs.elements["textcombined"][tt.name])

        if X is None:
            X = slab.getAxis(-1)
        if Y is None:
            Y = slab.getAxis(-2)
        wc2 = vcs.utils.getworldcoordinates(gm, X, Y)
        wc2 = kargs.get("plotting_dataset_bounds", wc2)
        vp2 = [self.data._x1, self.data._x2, self.data._y1, self.data._y2]
        vp2 = kargs.get("ratio_autot_viewport", vp2)

        # Do the tickmarks/labels
        if not isinstance(gm, vcs.taylor.Gtd):
            for axis in ["x", "y"]:
                for number in ["1", "2"]:
                    for mintic in [False, True]:
                        displays += self.drawTicks(slab,
                                                   gm,
                                                   x,
                                                   axis=axis,
                                                   number=number,
                                                   vp=vp2,
                                                   wc=wc2,
                                                   bg=bg,
                                                   X=X,
                                                   Y=Y,
                                                   mintic=mintic,
                                                   **kargs)

        if X is None:
            X = slab.getAxis(-1)
        if Y is None:
            Y = slab.getAxis(-2)

        wc2 = vcs.utils.getworldcoordinates(gm, X, Y)
        wc2 = kargs.get("plotting_dataset_bounds", wc2)

        # Do the boxes and lines
        for tp in ["box", "line"]:
            for num in ["1", "2"]:
                e = getattr(self, tp + num)
                if e.priority != 0:
                    ln_tmp = x.createline(source=e.line)
                    if hasattr(gm, "projection"):
                        ln_tmp.projection = gm.projection
                    if vcs.elements["projection"][
                            ln_tmp.projection].type != "linear":
                        ln_tmp.worldcoordinate = wc2[:4]
                        ln_tmp.viewport = kargs.get("ratio_autot_viewport",
                                                    [e._x1, e._x2, e._y1, e._y2])
                        dx = (e._x2 - e._x1) / \
                            (self.data.x2 - self.data.x1) * (wc2[1] - wc2[0])
                        dy = (e._y2 - e._y1) / \
                            (self.data.y2 - self.data.y1) * (wc2[3] - wc2[2])
                        if tp == "line":
                            ln_tmp._x = [wc2[0], wc2[0] + dx]
                            ln_tmp._y = [wc2[2], wc2[2] + dy]
                        elif tp == "box" and \
                                vcs.elements["projection"][ln_tmp.projection].type in\
                                round_projections:
                            ln_tmp._x = [[wc2[0], wc2[1]], [wc2[0], wc2[1]]]
                            ln_tmp._y = [[wc2[3], wc2[3]], [wc2[2], wc2[2]]]
                        else:
                            ln_tmp._x = [
                                wc2[0],
                                wc2[0] + dx,
                                wc2[0] + dx,
                                wc2[0],
                                wc2[0]]
                            ln_tmp._y = [wc2[2], wc2[2], wc2[3], wc2[3], wc2[2]]

                            # print('boxorline, wc2 = ', wc2)
                    else:
                        ln_tmp._x = [e._x1, e._x2, e._x2, e._x1, e._x1]
                        ln_tmp._y = [e._y1, e._y1, e._y2, e._y2, e._y1]
                    ln_tmp._priority = e._priority
                    displays.append(x.plot(ln_tmp, bg=bg, ratio="none", **kargs))
                    del(vcs.elements["line"][ln_tmp.name])

        # x.mode=m
        # I think i have to use dict here because it's a valid value
        # (obviously since i got it from the object itself and didn't touch it
        # but Dean doesn't allow to set it back to some of these values (None)!
        x._viewport = vp
        x._worldcoordinate = wc
        return displays

    def drawColorBar(self, colors, levels, legend=None, ext_1='n',
                     ext_2='n', x=None, bg=False, priority=None,
                     cmap=None, style=['solid'], index=[1],
                     opacity=[], pixelspacing=[15, 15], pixelscale=12, **kargs):
        """
        This function, draws the colorbar, it needs:

        colors : The colors to be plotted
        levels : The levels that each color represent
        legend : To overwrite, saying just draw box at
        certain values and display some specific text instead of the value
        ext_1 and ext_2: to draw the arrows
        x : the canvas where to plot it
        bg: background mode ?
        returns a list of displays used
        :param colors:
        :param levels:
        :param legend:
        :param ext_1:
        :param ext_2:
        :param x:
        :param bg:
        :param priority:
        :param cmap:
        :param style:
        :param index:
        :param opacity:
        :param kargs:
        :return:

        .. pragma: skip-doctest TODO add example/doctest. And more documentation...
        """

        kargs["donotstoredisplay"] = True
        displays = []
        #
        # Create legend
        #

        # Are levs contiguous?
        if isinstance(levels[0], (list, tuple)):
            levs2 = []
            cont = True
            for i in range(len(levels) - 1):
                if levels[i][1] == levels[i + 1][0]:
                    levs2.append(levels[i][0])
                else:  # Ok not contiguous
                    cont = False
                    break
            if cont:
                levs2.append(levels[-1][0])
                levs2.append(levels[-1][1])
                levels = levs2

        # Now sets the priority value
        if priority is None:
            priority = self.legend.priority
        # Now resets the viewport and worldcoordinate
        vp = x.viewport  # preserve for later restore
        wc = x.worldcoordinate  # preserve for later restore
        x.viewport = [0., 1., 0., 1.]
        x.worldcoordinate = [0., 1., 0., 1.]
        # Ok first determine the orientation of the legend (bottom to top  or
        # left to right)
        dX = abs(self.legend.x2 - self.legend.x1)
        dY = abs(self.legend.y2 - self.legend.y1)
        nbox = len(colors)
        if isinstance(levels[0], list):
            l0 = levels[0][0]
            l1 = levels[-1][1]
        else:
            l0 = levels[0]
            l1 = levels[-1]
        if l0 < -1.e19:
            ext_1 = 'y'
        if l1 > 1.e19:
            ext_2 = 'y'
        levels = list(levels)
        # Now figure out the typical length of a box
        if dX > dY:
            isHorizontal = True
            length = dX
            boxLength = dX / nbox
            thick = dY
            startLength = min(self.legend.x1, self.legend.x2)
            startThick = min(self.legend.y1, self.legend.y2)
        else:
            isHorizontal = False
            length = dY
            boxLength = dY / nbox
            thick = dX
            startLength = min(self.legend.y1, self.legend.y2)
            startThick = min(self.legend.x1, self.legend.x2)
        # initialize the fillarea coordinates
        L = []  # length
        T = []  # thickness
        # computes the fillarea coordinates
        iext = 0  # To know if we changed the dims
        if (ext_1 in ['y', 1, True] or ext_2 in ['y', 1, True]):  # and boxLength < self.legend.arrow * length:
            iext = 1  # one mins changed ext_1
            arrowLength = self.legend.arrow * length
            if ext_1 in ['y', 1, True] and ext_2 in ['y', 1, True]:
                boxLength = (length - 2. * arrowLength) / (nbox - 2.)
                iext = 3  # changed both side
            else:
                boxLength = (length - arrowLength) / (nbox - 1.)
                if ext_2 in ['y', 1, True]:
                    iext = 2

        # Loops thru the boxes (i.e colors NOT actual boxes drawn)
        adjust = 0
        for i in range(nbox):
            if ext_1 in ['y', 1, True] and i == 0:
                # Draws the little arrow at the begining
                # Make sure the triangle goes back to first point
                # Because used to close the extension
                L.append([
                    startLength + arrowLength,
                    startLength,
                    startLength + arrowLength,
                ])
                T.append(
                    [
                        startThick,
                        startThick + thick / 2.,
                        startThick + thick,
                    ])
                # Now readjust startLength if necessary
                if iext == 1 or iext == 3:
                    startLength = startLength + arrowLength
                    adjust = -1
            elif ext_2 in ['y', 1, True] and i == nbox - 1:
                # Draws the little arrow at the end
                L.append([
                    startLength + boxLength * (i + adjust),
                    startLength + boxLength * (i + adjust) + arrowLength,
                    startLength + boxLength * (i + adjust),
                ])
                T.append(
                    [
                        startThick,
                        startThick + thick / 2.,
                        startThick + thick,
                    ])
            else:
                # Draws a normal box
                L.append([startLength + boxLength * (i + adjust),
                          startLength + boxLength * (i + adjust + 1),
                          startLength + boxLength * (i + adjust + 1),
                          startLength + boxLength * (i + adjust)])
                T.append([startThick,
                          startThick,
                          startThick + thick,
                          startThick + thick])

        fa = x.createfillarea()
        fa.color = colors
        fa.style = style
        fa.index = index
        fa.priority = self.legend.priority
        # Boxfill default comes in here with [] we need to fix this
        if opacity == []:
            opacity = [None, ] * len(colors)
        fa.opacity = opacity
        fa.priority = priority
        fa.pixelspacing = pixelspacing
        fa.pixelscale = pixelscale
        if cmap is not None:
            fa.colormap = cmap
        # assigning directly since we gen it we know it's good
        if isHorizontal:
            fa._x = L
            fa._y = T
        else:
            fa._x = T
            fa._y = L
        displays.append(x.plot(fa, bg=bg, **kargs))
        del(vcs.elements["fillarea"][fa.name])
        # Now draws the box around the legend
        # First of all make sure we draw the arrows
        Tl = []  # Thickness labels location
        Ll = []  # Length labels location
        Tt = []  # Thickness ticks location
        Lt = []  # Length ticks location
        St = []  # String location
        levelsLength = length  # length of the levels area
        if ext_1 in ['y', 1, True]:
            Tl.append(T[0])
            Ll.append(L[0])
            levels.pop(0)
            if iext == 1 or iext == 3:
                levelsLength = levelsLength - arrowLength
        if ext_2 in ['y', 1, True]:
            Tl.append(T[-1])
            Ll.append(L[-1])
            levels.pop(-1)
            if iext > 1:
                levelsLength = levelsLength - arrowLength
        # adds the coordinate for the box around the legend
        Tl.append([startThick,
                   startThick,
                   startThick + thick,
                   startThick + thick,
                   startThick])
        Ll.append([startLength,
                   startLength + levelsLength,
                   startLength + levelsLength,
                   startLength,
                   startLength])
        # Now make sure we have a legend
        if isinstance(levels[0], list):
            # Ok these are non-contiguous levels, we will use legend only if
            # it's a perfect match
            for i, l in enumerate(levels):
                lt = l[0]
                lb = l[1]
                loc = i * boxLength + startLength
                Ll.append([loc, loc])
                Tl.append([startThick, startThick + thick])
                if legend is not None:
                    lt = legend.get(lt, None)
                    lb = legend.get(lb, None)
                if lt is not None:
                    loct = startLength + (i + .5) * boxLength
                    St.append(str(lt))
                    Lt.append(loct)
                    Tt.append(startThick + thick * 1.4)
                if lb is not None:
                    loct = startLength + (i + .5) * boxLength
                    St.append(str(lb))
                    Lt.append(loct)
                    Tt.append(startThick - thick * .6)

        else:
            if legend is None:
                legend = vcs.mklabels(levels)
            # We'll use the less precise float epsilon since this is just for labels
            if levels[0] < levels[1]:
                comparison = epsilon_lte
            else:
                comparison = epsilon_gte

            def in_bounds(x):
                return comparison(levels[0], x) and comparison(x, levels[-1])

            boxLength = levelsLength / (len(levels) - 1.)

            for il, l in enumerate(sorted(legend.keys())):
                if in_bounds(l):
                    for i in range(len(levels) - 1):
                        # if legend key is (inclusive) between levels[i] and levels[i+1]
                        if comparison(levels[i], l) and comparison(l, levels[i + 1]):
                            # first let's figure out where to put the legend label
                            location = i * boxLength  # position at beginning of level
                            # Adds the distance from beginning of level box
                            location += (l - levels[i]) / (levels[i + 1] - levels[i]) * boxLength
                            location += startLength  # Figures out the beginning

                            if not (numpy.allclose(l, levels[0]) or numpy.allclose(l, levels[-1])):
                                Ll.append([location, location])
                                Tl.append([startThick, startThick + thick])
                            Lt.append(location)
                            Tt.append(startThick + thick + self.legend.offset)
                            St.append(legend[l])
                            break
        # ok now creates the line object and text object
        ln = x.createline(source=self.legend.line)
        txt = x.createtext(
            To_source=self.legend.textorientation,
            Tt_source=self.legend.texttable)
        txt.string = St
        if isinstance(legend, list):
            if isHorizontal:
                txt.halign = "center"
            else:
                txt.valign = "half"
        if isHorizontal:
            ln._x = Ll
            ln._y = Tl
            txt.x = Lt
            txt.y = Tt
        else:
            ln._x = Tl
            ln._y = Ll
            txt.x = Tt
            txt.y = Lt

        # Now reset the viewport and worldcoordiantes
        displays.append(x.plot(ln, bg=bg, **kargs))
        displays.append(x.plot(txt, bg=bg, **kargs))
        del(vcs.elements["line"][ln.name])
        sp = txt.name.split(":::")
        del(vcs.elements["texttable"][sp[0]])
        del(vcs.elements["textorientation"][sp[1]])
        del(vcs.elements["textcombined"][txt.name])
        x._viewport = vp
        x._worldcoordinate = wc
        return displays

    def ratio_linear_projection(self, lon1, lon2, lat1, lat2,
                                Rwished=None, Rout=None,
                                box_and_ticks=0, x=None):
        """Computes ratio to shrink the data area of a template such that the
        overall area has the least possible deformation in linear projection

        .. note::

            lon1/lon2 must be specified in degrees east.
            lat1/lat2 must be specified in degrees north.

        :Example:

            .. doctest:: template_P_ratio_linear_projection

                >>> t=vcs.gettemplate()
                >>> t.ratio_linear_projection(-135,-50,20,50) # USA

        :param lon1: Start longitude for plot.
        :type lon1: `float`_ or `int`_

        :param lon2: End longitude for plot
        :type lon2: `float`_ or `int`_

        :param lat1: Start latitude for plot.
        :type lat1: `float`_ or `int`_

        :param lat2: End latitude for plot
        :type lat2: `float`_ or `int`_

        :param Rwished: Ratio y/x wished.
            If None, ratio will be determined automatically.
        :type Rwished: `float`_ or `int`_

        :param Rout: Ratio of output (default is US Letter=11./8.5)
            Also you can pass a string: "A4","US LETTER", "X"/"SCREEN",
            the latest uses the window information
            box_and_ticks: Also redefine box and ticks to the new region.
            If None, Rout will be determined automatically.
        :type Rout: `float`_ or `int`_
        """

        # Converts lat/lon to rad
        Lat1 = lat1 / 180. * numpy.pi
        Lat2 = lat2 / 180. * numpy.pi
        Lon1 = lon1 / 180. * numpy.pi
        Lon2 = lon2 / 180. * numpy.pi

        if (Lon1 == Lon2) or (Lat1 == Lat2):
            return

        if Rwished is None:
            Rwished = float(2 *
                            (numpy.sin(Lat2) -
                             numpy.sin(Lat1)) /
                            (Lon2 -
                                Lon1) /
                            (1. +
                                (numpy.sin(2 *
                                           Lat2) -
                                 numpy.sin(2 *
                                           Lat1)) /
                                2. /
                                (Lat2 -
                                 Lat1)))
        self.ratio(Rwished, Rout, box_and_ticks, x)
        return

    def ratio(self, Rwished, Rout=None, box_and_ticks=True, x=None):
        """Computes ratio to shrink the data area of a template
        to have an y/x ratio of Rwished
        has the least possible deformation in linear projection

        :Example:

            .. doctest:: template_P_ratio

                >>> t=vcs.gettemplate()
                >>> t.ratio(2) # y is twice x

        :param Rwished: Ratio y/x wished.
            Rwished MUST be provided.
        :type Rwished: `float`_ or `int`_

        :param Rout: Ratio of output (default is SCREEN).
            Also you can pass a string: "A4","US LETTER",
            "X"/"SCREEN", the latest uses the window information
            box_and_ticks: Also redefine box and ticks to the new region
        :type Rout: str or None

        :param box_and_ticks: Also scale the boxes and ticks default True
        :type box_and_ticks: `int` or `bool`

        :returns: vcs template object
        :rtype: vcs.template.P
        """
        if x is None:
            x = vcs.init()
        if isinstance(Rout, str):
            if Rout.lower() == 'a4':
                Rout = 29.7 / 21.
                if x.isportrait():
                    Rout = 1. / Rout
            elif Rout.lower() in ['us letter', 'letter',
                                  'us_letter', 'usletter']:
                Rout = 11. / 8.5
                if x.isportrait():
                    Rout = 1. / Rout
            elif Rout.lower() in ['x', 'x11', 'screen']:
                if x.iscanvasdisplayed():  # do we have the canvas opened ?
                    info = x.canvasinfo()
                    Rout = float(info['width']) / float(info['height'])
                else:  # Not opened yet, assuming default size: 959/728
                    Rout = 1. / .758800507
                    if x.isportrait():
                        Rout = 1. / Rout
        elif Rout is None:
            try:
                info = x.canvasinfo()
                Rout = float(info['width']) / float(info['height'])
            except Exception:
                Rout = 1. / .758800507
                if x.isportrait():
                    Rout = 1. / Rout

        t = x.createtemplate(source=self.name)

        # Computes the template ratio
        Rt = (self.data.y2 - self.data.y1) / (self.data.x2 - self.data.x1)

        # Actual ratio template and output format combined
        Ra = Rt / Rout
        # Ra=(self.data.y2-self.data.y1)/(self.data.x2-self.data.x1)
        if Rwished > Ra:
            t.scale(Ra / Rwished, axis='x')
        else:
            t.scale(Rwished / Ra, axis='y')
        ndx = t.data._x2 - t.data._x1
        ndy = t.data._y2 - t.data._y1

        odx = self.data._x2 - self.data._x1
        ody = self.data._y2 - self.data._y1

        self.data._x1 = t.data._x1
        self.data._x2 = t.data._x2
        self.data._y1 = t.data._y1
        self.data._y2 = t.data._y2

        if odx != ndx:
            self.data._x1 = max(0, min(1, self.data.x1 + (odx - ndx) / 2.))
            self.data._x2 = max(0, min(1, self.data.x2 + (odx - ndx) / 2.))
        else:
            self.data._y1 = max(0, min(1, self.data.y1 + (ody - ndy) / 2.))
            self.data._y2 = max(0, min(1, self.data.y2 + (ody - ndy) / 2.))

        if box_and_ticks:
            # Used to calculate label positions
            x_scale = ndx / float(odx)
            y_scale = ndy / float(ody)

            x_label_name_diff = self.xlabel1.y - self.xname.y
            y_label_name_diff = self.ylabel1.x - self.yname.x

            # Box1 resize
            self.box1._x1 = self.data._x1
            self.box1._x2 = self.data._x2
            self.box1._y1 = self.data._y1
            self.box1._y2 = self.data._y2
            # xLabel distance save
            dY1 = self.xlabel1._y - self.xtic1._y1
            dY2 = self.xlabel2._y - self.xtic2._y1
            # xLabel distance save
            dX1 = self.ylabel1._x - self.ytic1._x1
            dX2 = self.ylabel2._x - self.ytic2._x1
            # X tic
            dy = self.xtic1._y2 - self.xtic1._y1
            self.xtic1._y1 = self.data._y1
            self.xtic1._y2 = max(0, min(1, self.xtic1.y1 + dy))
            dy = self.xtic2._y2 - self.xtic2._y1
            self.xtic2._y1 = self.data._y2
            self.xtic2._y2 = max(0, min(1, self.xtic2.y1 + dy))
            # Xmin tic
            dy = self.xmintic1._y2 - self.xmintic1._y1
            self.xmintic1._y1 = self.data._y1
            self.xmintic1._y2 = max(0, min(1, self.xtic1._y1 + dy))
            dy = self.xmintic2._y2 - self.xmintic2._y1
            self.xmintic2._y1 = self.data._y2
            self.xmintic2._y2 = max(0, min(1, self.xmintic2._y1 + dy))
            # Y tic
            dx = self.ytic1._x2 - self.ytic1._x1
            self.ytic1._x1 = self.data._x1
            self.ytic1._x2 = max(0, min(1, self.ytic1._x1 + dx))
            dx = self.ytic2._x2 - self.ytic2._x1
            self.ytic2._x1 = self.data._x2
            self.ytic2._x2 = max(0, min(1, self.ytic2._x1 + dx))
            # Ymin tic
            dx = self.ymintic1._x2 - self.ymintic1._x1
            self.ymintic1._x1 = self.data._x1
            self.ymintic1._x2 = max(0, min(1, self.ymintic1._x1 + dx))
            dx = self.ymintic2._x2 - self.ymintic2._x1
            self.ymintic2._x1 = self.data._x2
            self.ymintic2._x2 = max(0, min(1, self.ymintic2._x1 + dx))
            # Xlabels
            self.xlabel1._y = max(0, min(1, self.xtic1._y1 + dY1))
            self.xlabel2._y = max(0, min(1, self.xtic2._y1 + dY2))
            # Ylabels
            self.ylabel1._x = max(0, min(1, self.ytic1._x1 + dX1))
            self.ylabel2._x = max(0, min(1, self.ytic2._x1 + dX2))

            # Axis Names
            self.xname.y = max(0, min(1, self.xlabel1._y - x_scale * x_label_name_diff))
            self.yname.x = max(0, min(1, self.ylabel1._x - y_scale * y_label_name_diff))
            self.data.ratio = -Rwished
        else:
            self.data.ratio = Rwished

        del(vcs.elements["template"][t.name])
        return
