# weewx-observerip
weewx driver for the Ambient ObserverIP weather station

Download the master branch tarball at https://github.com/dkmcode/weewx-observerip/archive/master.tar.gz


## Independent continuation

This repository retains dkmcode/weewx-observerip history and GPL-3.0-only
licensing. Version 0.2.1 supports Python 3 and WeeWX 5, byte-oriented UDP
probes, bounded HTTP requests and HTML parsing that terminates at EOF.

```
weectl extension install https://github.com/weewx-packages/weewx-observerip/archive/refs/tags/v0.2.1.zip
weectl station reconfigure --driver=user.observerip --config=/path/to/weewx.conf
```

A temperature unit mismatch now raises WeeWxIOError instead of NameError.
Set the ObserverIP station's displayed temperature to degF for this driver's US
unit mapping. The direct mode expects the units in `expected_units` and logs
the mismatched field. It does not reinterpret Celsius readings as Fahrenheit.

`mode = indirect` uses the configured transfer file. New installations using
HTTP interception can also use the WeeWX interceptor driver's ObserverIP support.
This driver retains direct firmware configuration and polling access.

Run `python -m pytest -q tests`. Tests use a local HTTP server and UDP responder,
plus unit mismatch and transfer-file fixtures. Actual firmware configuration
writes and Ambient ObserverIP device discovery remain to verify on a device.
