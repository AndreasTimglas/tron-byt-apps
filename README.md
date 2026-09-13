# Tronbyt Apps

Custom Pixlet apps for Tronbyt LED displays. Each app lives in its own folder under `apps/`.

## Apps

- [OpenMeteo Weather](apps/openmeteo/README.md): compact 64×32 Celsius weather using Open-Meteo, with a configurable location and no API key.

## Run OpenMeteo Weather

```sh
cd apps/openmeteo
pixlet check openmeteo.star
pixlet render openmeteo.star
pixlet serve openmeteo.star
```

Choose Location in the configuration UI or Tronbyt Manager. See the app README for details.
