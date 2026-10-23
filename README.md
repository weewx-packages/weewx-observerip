# Ambient ObserverIP for WeeWX

Read an Ambient ObserverIP weather station by polling its local HTTP pages, or
consume a transfer file produced by an intercepted Weather Underground upload.
Direct acquisition uses a UDP discovery probe as well as HTTP. This is local
station access, not an Ambient Weather cloud API client.

This independent continuation preserves
[dkmcode/weewx-observerip](https://github.com/dkmcode/weewx-observerip) history.
Use catalog archive **0.2.1.post20261022**. It contains the 0.2.1 runtime and
installs Apache examples inside the managed user tree. The older 0.2.1 archive
is withdrawn from the catalog; do not use its installer layout.

## Install

An existing WeeWX station is required. Replace `/path/to/weewx.conf`
with its configuration file before running the commands.

The catalog release requires Python >=3.10 and WeeWX >=5.2,<6.

Use the `weectl` from your WeeWX Python environment:

```sh
weectl extension install https://github.com/weewx-packages/catalog/releases/download/observerip/v0.2.1.post20261022/observerip-0.2.1.post20261022.tar.gz --config=/path/to/weewx.conf
weectl station reconfigure --driver=user.observerip --config=/path/to/weewx.conf
```

Stock WeeWX 5 accepts this fixed URL or a downloaded copy of the same archive.
No catalog integration is required. Restart WeeWX yourself after configuration
changes.

## Poll the station directly

The runtime needs WeeWX and the Python standard library. Put the ObserverIP and
WeeWX host on the same LAN segment so the UDP discovery exchange can reach them.
An explicit `hostname` directs the probe to that device; it does not remove the
UDP requirement.

```ini
[Station]
    station_type = ObserverIP
[ObserverIP]
    driver = user.observerip
    mode = direct
    hostname = 192.0.2.10
    poll_interval = 16
    dup_interval = 2
    check_calibration = false
    set_calibration = false
```

Replace the address. `mode` selects acquisition; the legacy `direct` setting
alone does not switch to transfer-file mode. The driver expects the station's
displayed temperature in degrees Fahrenheit and its other values in the units
listed in `expected_units` in [observerip.py](bin/user/observerip.py).
A mismatch stops acquisition instead of treating Celsius as Fahrenheit.

The installer supplies calibration defaults and enables `check_calibration`.
Review them before enabling checks. `set_calibration = true` permits writes to
the device; leave it false unless you intend to apply those offsets. Rain uses
cumulative totals to calculate increments.

## Read intercepted uploads

Use `mode = indirect`, `poll_interval = 17`, `check_calibration = false` and
`xferfile = /path/to/transfer/file` under `[ObserverIP]`. Arrange for the file to
be writable by the web server and readable by WeeWX. The included Apache/CGI
examples need manual deployment and adaptation:

* Installed configuration: `bin/user/observerip_examples/apache/conf.d/weatherstation-intercept.conf`.
* Installed handler: `bin/user/observerip_examples/apache/weatherstation/updateweatherstation.php`.

These paths are relative to your station root. The source examples remain under
[util/apache](util/apache). Despite its `.php` suffix, the handler is a Bash CGI
script and needs Bash and `bc`, plus `curl` only for its optional forwarding.
Configure Apache CGI handling, request redirection, file paths and permissions
yourself. Set the ObserverIP Relative Pressure Offset to zero for that example.
The installer neither configures Apache nor enables interception or forwarding.

Restart WeeWX after changing configuration and inspect its logs. Discovery,
firmware configuration writes and actual device/Apache behavior were not tested
in this documentation refresh. Device configurator options include
`--findobserver`, `--getdata` and `--defaultconfig`; inspect them with
`weectl device --help --config=/path/to/weewx.conf` after selecting this driver.

Copyrights and origin are preserved in [LICENSE](LICENSE), [NOTICE](NOTICE) and
the source headers. Distributed under GPL-3.0-only.

<!-- Documentation updated 2026-10-23 by weewx-packages. -->
