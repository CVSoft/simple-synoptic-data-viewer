import argparse
import os
import os.path
import json

import requests

VERSION = 0x0101


def clamp(test, lower, upper):
    """Force a number to be within a given range, with minimal efficiency."""
    return max(lower, min(upper, test))

def binnify(test, lower, upper, bins):
    """Compute a bin index for the 'sounding' raster display."""
    # No, I don't remember why this works. It's not hard to figure out though.
    bins -= 1
    ul = upper-lower
    bs = ul/bins
    return max(0, int(round(min(bins, bins*(test-lower)/ul), 0)))

def get_api_key(fn=None, is_token=True):
    """Read a token or key from a file. Validate the token (in the future)."""
    if not fn: fn = "api"+os.path.extsep+"apikey"
    if not os.path.exists(fn):
        raise FileNotFoundError
    with open(fn, 'r') as f:
        key = f.readline().strip()
        if is_token:
            if len(key) != 32: key = "0"*(32-len(key))+key
    if is_token: pass # input validation
    return key

def mb_to_hgt(Psta, mslp=1013.25): # METERS
    """Convert millibars to expected altitude, in meters."""
    return (1-(Psta/mslp)**0.190284)*44307.69396

def hgt_to_mb(hgt, mslp=1013.25):
    """Convert altitude, in meters, to expected millibars."""
    return mslp*(1-hgt/44307.69396)**5.2553026


class Synoptics(object):
    """Main class for reading and processing data from Synoptic Labs."""
    def __init__(self, token_fn=None):
        self.c_startstop = "%"
        self.c_range = "."
        self.c_data = ":"
        self.c_mean = "#"
        self.token = get_api_key(token_fn)
        self.lr = []

    def from_latest(self, radius=None, wvars=None, need_all_vars=False,
                    enable_wind=False,
                    get_all_stations=False, within=15):
        """Fetch current data from Synoptic Data"""
        if not radius:
            with open("default_radius.txt", "r") as f:
                radius = tuple(f.readline().strip().split(','))
                # input validation?
        assert len(radius) == 3, "Incorrect radius parameter."
        if not wvars or need_all_vars:
            wvars = ("air_temp","dew_point_temperature","pressure")
        if enable_wind:
            wvars += ("wind_speed", "wind_gust")
        params = {"vars": ','.join(wvars),
                  "varsoperator":("or" if need_all_vars else "and"),
                  "token": self.token,
                  "radius": "{},{},{}".format(*radius),
                  "status": "active",
                  "within": within}
        if get_all_stations: # skip preselection by variable selection (LARGE!)
            del params["vars"]
            del params["varsoperator"]
        r = requests.get("https://api.synopticdata.com/v2/stations/latest",
                         params=params)
        with open("last_result.json", "wb") as f:
            f.write(r.content)
        jd = r.json()
        self._create_result(jd)

    def from_file(self, fn="last_result.json"):
        """Fetch possibly stale data from a JSON file"""
        with open(fn, "r") as f:
            jd = json.load(f)
        self._create_result(jd)

    def _create_result(self, jd):
        """Create Last Result from JSON data"""
        self.lr = []
        for s in jd["STATION"]:
            try: self.lr.append(Station(s))
            except KeyError:
                print("Error in parsing a station. Stab the developer.")

    def prune(self, by):
        """Prune by presence of an attribute in a Station"""
        i = 0
        print(by)
        while True:
            if getattr(self.lr[i], by, None) == None: del self.lr[i]
            else: i += 1
            if i >= len(self.lr): break

    def elev_range(self, key="pres_uc"):
        """Find the lowest and highest elevations"""
        el = list(map(lambda q:getattr(q, key, None), self.lr))
        return [max(el), min(el)]

    def _tmp_range(self, key="temp"):
        """Find the lowest and highest temperatures"""
        # Internal use only, as we don't validate whether we actually have
        #   the data. self.prune(key) does that, but why do it twice?
        tl = list(map(lambda q:getattr(q, key, None), self.lr))
        return [min(tl), max(tl)]

    def report_temp_vs_pres(self, xl=50, yl=21, min_temp=None, min_pres=None,
                            max_pres=None, max_temp=None, key="pres",
                            show_console=True, out_json=None, xkey="temp"):
        """Create and process the temperature vs. pressure report"""
        if min_temp == None: min_temp = -1000
        if max_temp == None: max_temp = 1000
        if min_pres == None: min_pres = 0
        if max_pres == None: max_pres = 10000
        jd = dict()
        assert key in ("pres_uc", "pres",
                       "elevation", "elevation_dem"), "Invalid y-axis"
        self.prune(key)
        self.prune(xkey)
        if len(self.lr) == 0:
            print("No data available to display.")
            return
        jd["x-axis"] = xkey
        jd["y-axis"] = key
        minmax = self.elev_range(key=key)
        if min_pres and "pres" in key:
            minmax[1] = clamp(minmax[1], min_pres, minmax[0]-10) # it works
        if max_pres and "pres" in key:
            minmax[0] = clamp(minmax[0], minmax[1]+10, max_pres)
        tminmax = self._tmp_range(key=xkey)
        tminmax = [clamp(tminmax[0], min_temp, tminmax[1]-10),
                   clamp(tminmax[1], tminmax[0]+10, max_temp)]
        jd["x-min"] = tminmax[0]
        jd["x-max"] = tminmax[1]
        jd["y-min"] = minmax[0]
        jd["y-max"] = minmax[1]
        # i think it's wise to use a data structure for this
        bins = [[] for i in range(yl)]
        tbins = [[" " for i in range(xl)] for j in range(yl)]
        stations = dict()
        for s in self.lr:
            bins[binnify(getattr(s, key), minmax[1], minmax[0], yl)].append(s)
            stations[s.sid] = [getattr(s, key), getattr(s, xkey)]
        jd["stations"] = stations
        for i in range(len(bins)):
            if not bins[i]: continue
            self.lr = bins[i]
            lt = self._tmp_range(key=xkey) # intermediate result
            tl = list(map(lambda q:getattr(q, xkey), bins[i]))
            ltr = [binnify(lt[0], tminmax[0], tminmax[1], xl),
                   binnify(lt[1], tminmax[0], tminmax[1], xl)]
            if ltr[0] == ltr[1]:
##                print("Equal bin = ", ltr)
                tbins[i][ltr[0]] = self.c_mean
            else:
                for s in bins[i]:
                    tbins[i][binnify(getattr(s, xkey),
                                     tminmax[0], tminmax[1],
                                     xl)] = self.c_data
                tbins[i][binnify(sum(tl)/len(tl),
                                 tminmax[0], tminmax[1],
                                 xl)] = self.c_mean
                tbins[i][ltr[0]] = self.c_startstop
                tbins[i][ltr[1]] = self.c_startstop
                for j in range(ltr[0]+1, ltr[1], 1):
                    if tbins[i][j] == " ": tbins[i][j] = self.c_range
        for i in range(len(tbins)):
            tbins[i] = "{:4d} |".format(\
                int(minmax[0]+(minmax[1]-minmax[0])*(yl-i-1)/yl))+\
                       ''.join(tbins[i])+"| n={:d}".format(len(bins[i]))
        if key in ("elevation", "elevation_dem"): tbins = tbins[::-1]
        tbins.insert(0, " "*5+"+"+"{:-^{width}s}".format(key+" vs "+xkey,
                                                         width=xl)+"+")
        tbins.append(" "*5+"+"+"-"*xl+"+")
        tbins.append(" "*6+("{:<3d}"+" "*(xl-5)+"{:>3d}").format(\
            int(tminmax[0]), int(tminmax[1])))
        jd["console_output"] = list(tbins)
        tbins = '\n'.join(tbins)
        if show_console: print(tbins)
        if out_json:
            with open(out_json, 'w') as f:
                json.dump(jd, f)


class Station(object):
    """Station data storage and validation class."""
    def __init__(self, data, verbose=False):
        self.verbose = verbose
        try:
            self.elevation = float(data["ELEVATION"])*0.3048
            self.pres_uc = hgt_to_mb(self.elevation)
        except TypeError:
            self.elevation = None
            self.pres_uc = None
        try:
            self.elevation_dem = float(data["ELEV_DEM"])*0.3048
            self.pres_uc_dem = hgt_to_mb(self.elevation_dem)
        except TypeError:
            self.elevation_dem = self.elevation
            self.pres_uc_dem = self.pres_uc
        self.id = data["ID"]
        self.sid = data["STID"]
        self.pos = data["LATITUDE"], data["LONGITUDE"]
        self.qcflag = data["QC_FLAGGED"]
        try:
            tm_key = list(data["SENSOR_VARIABLES"]\
                          ["air_temp"].keys())[0]
            self.temp = data["OBSERVATIONS"][tm_key]["value"]
        except:
            self.temp = None
            if self.verbose:
                print("Didn't find Temperature for", self.sid)
                print("Keys:", list(data["SENSOR_VARIABLES"].keys()))
        try:
            dp_key = list(data["SENSOR_VARIABLES"]\
                          ["dew_point_temperature"].keys())[0]
            self.dewp = data["OBSERVATIONS"][dp_key]["value"]
        except:
            self.dewp = None
            if self.verbose:
                print("Didn't find Dewpoint for", self.sid)
                print("Keys:", list(data["SENSOR_VARIABLES"].keys()))
        try:
            pa_key = list(data["SENSOR_VARIABLES"]\
                          ["pressure"].keys())[0]
            self.pres = data["OBSERVATIONS"][pa_key]["value"]/100.
        except:
            self.pres = None
            if self.verbose:
                print("Didn't find Pressure for", self.sid)
                print("Keys:", list(data["SENSOR_VARIABLES"].keys()))
        try:
            ws_key = list(data["SENSOR_VARIABLES"]\
                          ["wind_speed"].keys())[0]
            self.wind = data["OBSERVATIONS"][ws_key]["value"]
        except:
            self.wind = None
            if self.verbose:
                print("Didn't find Wind Speed for", self.sid)
                print("Keys:", list(data["SENSOR_VARIABLES"].keys()))
        try:
            wg_key = list(data["SENSOR_VARIABLES"]\
                          ["wind_gust"].keys())[0]
            self.gust = data["OBSERVATIONS"][wg_key]["value"]
        except:
            self.gust = None
            if self.verbose:
                print("Didn't find Wind Gust for", self.sid)
                print("Keys:", list(data["SENSOR_VARIABLES"].keys()))


if __name__ == "__main__":
    a = argparse.ArgumentParser(description="""\
Synoptic Data Visualizer, version {:d}.{:02x}
Grabs data from weather stations and creates a plot of temperature vs. \
altitude.\
""".format(VERSION >> 8, VERSION & 0x0FF),
                                prefix_chars="-",
                                add_help=False)
    a.add_argument("-?", "-h", "--help", action="help",
                   help="Show this help message and exit.")
    a.add_argument("-v", "--version", action="version",
                   help="Show program version info",
                   version="%(prog)s v{:d}.{:02x}".format(VERSION >> 8,
                                                         VERSION & 0x0FF))

    a.add_argument("-r", "--radius", type=str, default=None,
                   help="Specify lat, lon, and miles radius to select \
stations. This info is passed directly to Synoptic.")
    a.add_argument("-s", "--dims", "--size", type=int, default=[66, 16],
                   nargs=2,
                   help="Width and height of the 'sounding' display")
    a.add_argument("-p", "--product", type=str, default="pres_uc",
                   choices=["pres", "pres_uc", "elevation", "elevation_dem"],
                   help="Select the product used for the Y-axis.")
    a.add_argument("-f", "--file", type=str, default="__LIVE__",
                   const="last_result.json", nargs='?',
                   help="Select a JSON file containing stored results. \
If no filename is specified, the Last Result file is used.")
    a.add_argument("-x", "--xkey", action="store", default="temp",
                   choices=["temp", "dewp", "wind", "gust"],
                   help="Select what mesonet value is being plotted.")
    a.add_argument("--pres-lower", type=int, default=850,
                   help="Minimum pressure (mbar) of the 'sounding' display. \
Default is 850.")
    a.add_argument("--pres-upper", type=int, default=1025,
                   help="Maximum pressure (mbar) of the 'sounding' display. \
Default is 1025.")
    a.add_argument("--temp-lower", type=int, default=None,
                   help="Minimum temperature (C) of the 'sounding' display. \
Default is 0.")
    a.add_argument("--temp-upper", type=int, default=None,
                   help="Maximum temperature (C) of the 'sounding' display.")
    a.add_argument("--within", type=int, default=15,
                   help="Maximum age of current observations (default is \
15 minutes.)")
    a.add_argument("--slim", action="count", default=0,
                   help="Only request the necessary variables for the current \
'sounding' display configuration from Synoptic.")
    a.add_argument("--all-params", action="count", default=0,
                   help="Require all parameters used by %(prog)s in the \
Synoptic data fetch. Use with --slim.")
    a.add_argument("--enable-wind", action="count", default=0,
                   help="Enable the use of wind parameters. Limits stations.")
    a.add_argument("-l", "--localize", type=str, default="%.:#",
                   help="Define the character set used for the display.")
    a.add_argument("-t", "--token", type=str, default=None,
                   help="Specify a Synoptic API token filename.")
    a.add_argument("--no-viz", action="count", default=0,
                   help="Do not show the 'sounding' display.")
    a.add_argument("--output", "-o", nargs=1, default=(None,), type=str,
                   help="Store output data to JSON.")
    args = a.parse_args()
    m = Synoptics(token_fn=args.token)
    if len(args.localize) == 4:
        m.c_startstop = args.localize[0]
        m.c_range = args.localize[1]
        m.c_data = args.localize[2]
        m.c_mean = args.localize[3]
    if args.file == "__LIVE__":
        print("Data source: live data from Synoptics API")
        need_products = []
        if args.xkey == "dewp": need_products.append("dew_point_temperature")
        elif args.xkey == "wind": need_products.append("wind_speed")
        elif args.xkey == "gust": need_products.append("wind_gust")
        else: need_products.append("air_temp")
        if args.product in ("pres",):
            need_products.append("pres")
        try:
            radius = tuple(map(float, args.radius.split(',')))
        except:
            radius = None
        m.from_latest(radius=radius,
                      need_all_vars=bool(args.all_params),
                      get_all_stations=not bool(args.slim),
                      enable_wind=bool(args.enable_wind),
                      wvars=need_products, within=args.within)
    else:
        print("Data source: saved data from file ({})".format(args.file))
        m.from_file(args.file)
    m.report_temp_vs_pres(xl=args.dims[0], yl=args.dims[1],
                          min_temp=args.temp_lower,
                          max_temp=args.temp_upper,
                          min_pres=args.pres_lower,
                          max_pres=args.pres_upper,
                          key=args.product,
                          out_json=args.output[0],
                          show_console=(args.no_viz == 0),
                          xkey=args.xkey)
