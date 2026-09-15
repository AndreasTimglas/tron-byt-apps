# Morris Rain

A 64×32 animated **three-hour precipitation forecast** centered on Morristown,
New Jersey (40.7968° N, 74.4815° W). A dark geographic map stays behind the
forecast precipitation echoes, with a white location marker at the center.

## Source: NOAA / National Weather Service

The forecast is NOAA/NCEP's operational **HRRR 1000 m above-ground simulated
radar reflectivity**, served by the free Iowa Environmental Mesonet (Iowa State
University) map API. NOAA/NCEP is part of the National Weather Service.
No API key, registration, OAuth, or secrets are required.

- [IEM HRRR service and dataset documentation](https://mesonet.agron.iastate.edu/GIS/model.phtml)
- [NOAA HRRR model](https://www.emc.ncep.noaa.gov/emc/pages/numerical_forecast_systems/hrrr.php)
- Model availability: `https://mesonet.agron.iastate.edu/data/gis/images/4326/hrrr/refd_1080.json`
- Per-frame timestamps: `https://mesonet.agron.iastate.edu/data/gis/images/4326/hrrr/refd_FFFF.json`
- Images: `https://mesonet.agron.iastate.edu/cgi-bin/wms/hrrr/refd.cgi`

`FFFF` is forecast lead time in **minutes**, zero-padded to four digits. Images
use WMS 1.1.1 GetMap, `LAYERS=refd_FFFF`, `SRS=EPSG:3857`, `WIDTH=64`, `HEIGHT=32`,
`FORMAT=image/png`, and `TRANSPARENT=TRUE`.

This is **forecast simulated radar**, not observed radar, literal cloud cover,
rain probability, or accumulated rainfall. `FCST` stays visible to identify it.
The original IEM N0Q reflectivity palette is retained: weak echoes can be gray
or blue, green represents lighter echoes, yellow/orange/red stronger echoes,
and pink/purple very intense echoes. These are intensity colors, not a countdown
or probability scale. Reflectivity can include snow or hail; this layer does
not distinguish precipitation type or guarantee rain reaches the ground.

## Map, radius, and marker

The requested radius is interpreted as approximately **175 miles from the
center to the left/right edges**, giving a roughly 350-mile-wide map. On a
2:1 display, the vertical extent is about 175 miles total (87.5 miles each side
of center). North is up. The map and forecast share this Web Mercator extent:

```text
-8663268.36,4796402.90,-7919216.94,5168428.61
```

Web Mercator scale varies with latitude; distances are approximate. Each pixel
represents about 5.5 miles near the center, so this is a regional overview.

The plus sign is three pixels wide and three pixels tall, using **five lit
pixels**. Three lit pixels alone cannot form a symmetric plus. Its center is
at (32,16), the nearest center pixel on the even-sized display, always drawn
above the precipitation layer.

`basemap.png` is an original pixel rendering of public-domain
[Natural Earth](https://www.naturalearthdata.com/about/terms-of-use/) land and
state boundaries. Source data:

- [110m land GeoJSON](https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_land.geojson)
- [110m state boundary GeoJSON](https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_admin_1_states_provinces_lines.geojson)

The static map includes coastline and state boundaries without dense road or
city labels. It requires no background-map requests at runtime.

## Time and refresh

Seven frames advance in 30-minute steps over three hours, starting at the first
15-minute model forecast time at or after rendering. The first time can be up
to 15 minutes ahead of now. Each frame lasts one second. The upper-right label
is its valid local time in **America/New_York**, with daylight saving handled
automatically. All seven frames come from one model initialization. Forecast
lead time accounts for model age; it is not simply initialization +1/+2/+3 hours.

The manifest recommends a **10-minute** refresh (`recommendedInterval: 10`).
A successful complete animation is cached for 600 seconds using Pixlet's
normal cache. Individual live WMS/metadata requests are not app-cached, to
avoid mixing runs. Model initialization is checked per frame and again at the
end; a change during fetching produces `UPDATING` rather than a mixed sequence.
Runs older than six hours produce `OLD MODEL`. The root carries a 20-minute
expiration hint, subject to host/device support. Set the app's display duration
to at least seven seconds in Manager to see the whole sequence.

## Run

From the repository root, with Tronbyt Pixlet v0.54.0 or newer:

```sh
pixlet check apps/morrisrain/morrisrain.star
pixlet render apps/morrisrain/morrisrain.star
pixlet serve apps/morrisrain/morrisrain.star
```

No configuration is required. In Tronbyt Manager, refresh the Custom Apps
Repository and add **Morris Rain**. On a slow network, the validation runtime
budget may need increasing:

```sh
pixlet check apps/morrisrain/morrisrain.star --max-render-time 20s
```

## Failure behavior and validation

HTTP errors, missing metadata, inconsistent run/time information, and non-PNG
responses show a compact error state. A transparent valid forecast image means
no echoes are visible; it is not automatically treated as missing data.
Incomplete forecasts are never replaced with invented rain or past radar.

Pixlet v0.54.0 cannot catch DNS/TLS/timeout failures from `http.get`, malformed
image decoder errors, or invalid timestamp parsing. Those remain host-handled.
Fresh cached animations need no network; once refresh is due, a transport error
cannot trigger an app-level fallback. Timestamp JSON and PNG signatures are
checked before passing data to the runtime.

Validated with Pixlet v0.54.0: standard `pixlet check`, live seven-frame rendering,
64×32 output, forecast timing with delayed model runs and UTC day rollover,
and a dry-region preview with the map and center marker. The current live test
contained no precipitation echoes; rain colors are supplied directly by IEM.
