# simple-synoptic-data-viewer
A command line tool for visualizing altitude vs. temperature using Synoptic Data API in Python 3. Requires [requests](https://pypi.org/project/requests/). 

![Screenshot of Simple Synoptic Data Viewer](https://i.imgur.com/0RLGODn.png)

# What?
This program fetches [data from Synoptic Data](https://developers.synopticdata.com/) and creates a plot of altitude vs. temperature. The altitude is displayed as expected air pressure at the station' altutude by default, although this can be changed to use actual air pressure measured at the station or just the station altitude. 

I wrote this in one sitting over about 6 hours, and my first time using `argparse` and the Synoptic Data API. It's not really a well-written project and I never intended it to be. Not all errors are caught, certain pieces of code are lazy workarounds to achieve expected behavior, and much of the behavior has not been tested. It seems to work, though. 

# What units does the output use?
Altitude is in meters, pressure is in millibars (hectopascals), and temperature is degrees Celsius. I neither check nor enforce units from the API (yet), although the temperature unit isn't really important except for setting the viewport ranges. 

# Where does the API token come from?
By default, this program looks in a text file named `api.apikey`, reads the first line, and uses that as the `token` parameter passed to Synoptic Data. Alternate locations for this file can be specified using a command line switch. You can get your own token by [signing up for Synoptic Data API access for free](https://developers.synopticdata.com/signup/). No, you can't have mine. 

# What do the command line switches do?
- `-f` reads data from a JSON file instead of fetching it from Synoptic Data. Data fetched from Synoptic Data is stored in `last_result.json`, and using `-f` without any arguments will read from this file. 
- `-s` sets the 'sounding' display viewport size, and takes two arguments (`-s 67 18`). 
- Product selection (for the Y-axis) can accept :
  - `pres` (pressure measured by the weather station), 
  - `pres_uc` ('uncalibrated' pressure expected at station altitude),
  - `elevation` (station elevation reported by the station), or
  - `elevation_dem` (station elevation derived from station positon and Synoptic Data's Digital Elevation Model)
- `-d` selects dewpoint as the temperature data source instead of air temperature. 
- `--slim` fetches only the parameters used by the current graph data source selections instead of the entire station status. This saves a lot of network bandwidth and API service units. Doesn't apply when reading a file. 
  - `--all-params` fetches all parameters understood by this program, and only those parameters. This allows different views of saved request data to be created without fetching a bunch of unused data from Synoptic Data. This switch must be used with `--slim`. I'll probably make this switch enabled by default later. 
- `--radius` specifies a lat, lon, and radius (miles, I believe) that is passed to Synoptic Data. Example: `-r 33.5,-118.0,25`. The default value of this parameter is stored in `default_radius.txt`, and if the radius isn't specified on the command line, this program looks in that text file for the parameter value (in the same format that you'd pass to the command line). 
- `--localize` changes the characters used for the display. It takes exactly four characters, described here in the expected order: 
  - the character used for the lowest and highest temperatures in an altitude bin (defaults to %),
  - the character used for filling in the space between the lowest and highest temperatures (defaults to .),
  - the character used for denoting temperature bins containing at least one station's observed value (defaults to :),
  - and the character used to highlight the mean temperature within an altitude bin (defaults to #).
- `--no-viz` skips displaying the 'sounding'. Useful with the JSON output option. 
- `-o filename` stores parsed data in JSON format. Nothing actually uses this data yet, but you might!
- The complete help file is below:
```
usage: mesonet.py [-?] [-v] [-r RADIUS] [-s DIMS DIMS]
                  [-p {pres,pres_uc,elevation,elevation_dem}] [-f [FILE]] [-d]
                  [--pres-lower PRES_LOWER] [--pres-upper PRES_UPPER]
                  [--temp-lower TEMP_LOWER] [--temp-upper TEMP_UPPER]
                  [--within WITHIN] [--slim] [--all-params] [-l LOCALIZE]
                  [-t TOKEN] [--no-viz] [--output OUTPUT]

Synoptic Data Visualizer, version 1.00 Grabs data from weather stations and
creates a plot of temperature vs. altitude.

optional arguments:
  -?, -h, --help        Show this help message and exit.
  -v, --version         Show program version info
  -r RADIUS, --radius RADIUS
                        Specify lat, lon, and miles radius to select stations.
                        This info is passed directly to Synoptic.
  -s DIMS DIMS, --dims DIMS DIMS, --size DIMS DIMS
                        Width and height of the 'sounding' display
  -p {pres,pres_uc,elevation,elevation_dem}, --product {pres,pres_uc,elevation,e
levation_dem}
                        Select the product used for the Y-axis.
  -f [FILE], --file [FILE]
                        Select a JSON file containing stored results. If no
                        filename is specified, the Last Result file is used.
  -d, --dewpoint        Use dewpoint instead of air temperature.
  --pres-lower PRES_LOWER
                        Minimum pressure (mbar) of the 'sounding' display.
                        Default is 850.
  --pres-upper PRES_UPPER
                        Maximum pressure (mbar) of the 'sounding' display.
                        Default is 1025.
  --temp-lower TEMP_LOWER
                        Minimum temperature (C) of the 'sounding' display.
                        Default is 0.
  --temp-upper TEMP_UPPER
                        Maximum temperature (C) of the 'sounding' display.
  --within WITHIN       Maximum age of current observations (default is 15
                        minutes.)
  --slim                Only request the necessary variables for the current
                        'sounding' display configuration from Synoptic.
  --all-params          Require all parameters used by mesonet.py in the
                        Synoptic data fetch. Use with --slim.
  -l LOCALIZE, --localize LOCALIZE
                        Define the character set used for the display.
  -t TOKEN, --token TOKEN
                        Specify a Synoptic API token filename.
  --no-viz              Do not show the 'sounding' display.
  --output OUTPUT, -o OUTPUT
                        Store output data to JSON.
```

# Todo
- A lot?
- Skew-T plot. Sounds harder than it actually should be. 
- Clean up redundant pieces of code
- Make the data visualizer more flexible (it was more of a gimmick when first added). 
