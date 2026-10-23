# ObserverIP

A WeeWX driver for the Ambient ObserverIP. In direct mode it finds the station
with a UDP probe and polls its local web pages. In indirect mode it reads a
transfer file that a CGI script writes from intercepted Weather Underground
uploads. It does not use the Ambient Weather cloud.

This is an independent continuation of
[dkmcode/weewx-observerip](https://github.com/dkmcode/weewx-observerip). See
[NOTICE](NOTICE).

## Requirements

- An Ambient ObserverIP whose units are set to `mph`, `in`, `inhg`, `degF`
  and `w/m2`. The driver does not convert units. In direct mode, and in
  indirect mode with `check_calibration = true`, it reads the unit settings
  from the station and stops on a mismatch.
- Direct mode: the station and the WeeWX host on the same network segment, so
  that UDP port 25122 reaches the station.
- Indirect mode: a web server that runs the CGI example and receives the
  station's uploads. The example script needs Bash and `bc`, and `curl` if it
  forwards uploads to Weather Underground.

The driver needs no Python packages beyond WeeWX.

## Installation

Install `observerip` from the [WeeWX packages catalog](https://github.com/weewx-packages/catalog/blob/main/packages/observerip.md).
The catalog page lists the current release, its WeeWX and Python
requirements, and the install, update and removal commands.

Then select the driver and restart WeeWX:

```sh
weectl station reconfigure --driver=user.observerip --config=/path/to/weewx.conf
```

The installer adds a `[[calibration]]` section with default values and sets
`check_calibration = false`. Compare those values with the calibration page of
your station before you turn the check on. See [Calibration](#calibration).

## Configuration

Direct mode:

```ini
[Station]
    station_type = ObserverIP

[ObserverIP]
    driver = user.observerip
    mode = direct
    poll_interval = 16
    dup_interval = 2
    check_calibration = false
```

Options in `[ObserverIP]`:

| Option | Default | Meaning |
|---|---|---|
| `mode` | `direct` | `direct` polls the station, any other value reads `xferfile`. |
| `hostname` | none | Address for the UDP probe. Without it the probe is a broadcast to 255.255.255.255. |
| `poll_interval` | `10` | Direct: seconds between packets. Indirect: seconds after the timestamp of the last packet before the file is read again. The installer writes `16`. |
| `dup_interval` | `5` | Seconds to wait after an empty, incomplete or duplicate packet. The installer writes `2`. |
| `xferfile` | none | Indirect mode: path of the transfer file. |
| `max_tries` | `5` | Attempts for the UDP probe, each HTTP page and each read of `xferfile`. |
| `retry_wait` | `2` | Seconds between attempts, also the UDP receive timeout. |
| `timeout` | `5` | HTTP timeout in seconds. |
| `check_calibration` | `false` | Compare the station calibration with `[[calibration]]` at startup. |
| `set_calibration` | `false` | On a mismatch, write `[[calibration]]` to the station. Only used with `check_calibration = true`. |

The UDP probe runs at every start in direct mode, and in indirect mode when
`check_calibration` is true. After the probe, the driver sends its HTTP
requests to the IP address the station reports in its reply, not to
`hostname`.

Every packet must contain all fields the driver maps, or it is dropped. Packets
with a timestamp not newer than the previous one are dropped as well. `rain`
is the increase of the yearly rain total, so the first packet after a start
has no `rain`.

### Calibration

With `check_calibration = true`, the driver compares each key in
`[[calibration]]` with the station's calibration page. A mismatch stops the
driver, unless `set_calibration = true`. Then the driver writes the values to
the station and checks again. Keys you leave out are not checked.

| Key | Installer value | Range accepted by `set_calibration` |
|---|---|---|
| `RainGain` | `1.0` | 0.1 to 5.0 |
| `windDirOffset` | `0` | -180 to 180 |
| `inHumiOffset` | `0` | -10 to 10 |
| `outHumiOffset` | `0` | -10 to 10 |
| `inTempOffset` | `0.0` | -18 to 18 |
| `outTempOffset` | `0.0` | -18 to 18 |
| `AbsOffset` | `0.00` | -23.62 to 23.62 |
| `RelOffset` | not set | -23.62 to 23.62 |
| `UVGain` | `1.00` | 0.1 to 5.0 |
| `SolarGain` | `1.00` | 0.1 to 5.0 |
| `WindGain` | `1.00` | 0.1 to 5.0 |
| `luxwm2` | `126.7` | 1 to 1000 |

### Reading intercepted uploads

```ini
[ObserverIP]
    driver = user.observerip
    mode = indirect
    poll_interval = 17
    dup_interval = 2
    xferfile = /path/to/transfer/file
    check_calibration = false
```

The installer copies two examples to `bin/user/observerip_examples/apache/`
in the WeeWX root. The sources are in
[bin/user/observerip_examples/apache](bin/user/observerip_examples/apache):

- `conf.d/weatherstation-intercept.conf` maps `/weatherstation/` to the CGI
  directory `/var/www/weatherstation/`.
- `weatherstation/updateweatherstation.php` is a Bash CGI script despite its
  suffix. It writes each upload as `name=value` lines to the file in its
  `xferfile` variable.

The installer does not configure the web server. To use the examples:

1. Copy the `.conf` file to the Apache configuration directory and check its
   paths.
2. Copy the script to `/var/www/weatherstation/` and make it executable.
3. Set `xferfile` in the script and in `weewx.conf` to the same file. The web
   server must be able to write it, WeeWX must be able to read it.
4. Set the Relative Pressure Offset on the station's calibration page to 0.
   The driver stores the uploaded `baromin` as `pressure`.
5. Redirect the station's Weather Underground uploads to this server. The
   script ends with a sample `iptables` destination NAT rule.

The script forwards the upload to Weather Underground only if `id` and
`passwd` are set in it. It rewrites the transfer file on each upload, so the
file holds only the latest upload.

The [interceptor](https://github.com/weewx-packages/catalog/blob/main/packages/interceptor.md)
driver can also receive ObserverIP uploads, without a CGI script.

### Device commands

After selecting the driver, `weectl device` offers these options:

```sh
weectl device --config=/path/to/weewx.conf --findobserver
weectl device --config=/path/to/weewx.conf --getdata
weectl device --config=/path/to/weewx.conf --defaultconfig
```

`--findobserver` prints the station URL, `--getdata` prints its live data,
`--defaultconfig` prints the default `[ObserverIP]` section. Each command runs
the UDP probe first.

## Limitations

- Tested with a local HTTP server, a UDP responder and transfer-file fixtures,
  not with an ObserverIP. Discovery, calibration writes and firmware behaviour
  are not verified on a device.
- The Apache configuration example is not tested. The CGI script is tested
  from the command line, not under a web server.
- The driver writes its log messages to syslog with the prefix `observerip:`,
  not through the WeeWX logging configuration.

## Development

```sh
python -m pytest -q tests
```

## License

Copyright 2015 David Malick. Distributed under GPL-3.0-only. See
[LICENSE](LICENSE), [NOTICE](NOTICE) and the source headers.
