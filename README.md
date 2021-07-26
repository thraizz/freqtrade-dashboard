# Freqtrade + Prometheus + Grafana = <3

This repo provides my current work on a metric exporter for [freqtrade](https://github.com/freqtrade/freqtrade).
The intended usage for this is to monitor multiple different running freqtrade instances, running different strategies.
You will be able to compare these against each other.
![Screenshot](https://lakur.tech/s/ffb2b12abbc515454a95c35fc5bfac3d9eace5b1.png)

## Installation
This whole repository is best used and intended to be used over the docker-compose.yml.
If you want to integrate the dashboard with your already present freqtrade instances, you have to add them to the same network the collector and prometheus resides in.
I always call this network the `metrics` network.
You have to create this shared network first by running `docker network create metrics`.
After this, you can run the example by running `docker-compose up -d`.
Inspecting the log output of the 

## Configuration
Ideally, we would set the clients over docker-compose vars, but currently they are all defined in the collector/main.py file.
There, you'll find the `BOTS` dict, which holds a name used for identifying the bot in grafana and the hostname.
The hostname should be the container name of your freqtrade instance.
Your username/password HAVE TO be the defaults for every instance, which is `freqtrader` and `SuperSecurePassword`.
If you want to change this, you have to change the base64 encoded Authorization header, which currently representes the default username and password.

The freqtrade configuration should set `listen_ip_adress` to `0.0.0.0`. The rest can be left as defaults.

After starting the instance, you should be able to visit grafana on localhost:8080. Setup your login credentials, then head over to the settings -> data sources. There, setup a new Prometheus data source. The URL is http://localhost:9090, the rest can remain as default values.
Once done, you can head over to the dashboard import (http://localhost:8080/dashboard/import) and upload the here included FreqtradeDashboard.json.
Now you'll see the (more or less) beautiful dashboard!


## Roadmap
Currently, we make heavy use of the api over direkt requests. This isnt too pretty, as there already is a API client provided by freqtrade.
In the future it would be nicer to switch to that API client.

