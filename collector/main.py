import argparse
import logging
import sys
import time

import requests

from prometheus_client import Metric, REGISTRY, start_http_server

# logging setup
log = logging.getLogger("freqtrade_exporter")
log.setLevel(logging.INFO)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
formatter = logging.Formatter("[%(levelname)s]: %(message)s")
ch.setFormatter(formatter)
log.addHandler(ch)


BOTS = {
        # "NAME_IN_GRAFANA": "CONTAINER_NAME:PORT"
        "ExampleBot": "freqtrade_combinedbinhandcluc:3000",
}


class Endpoint:
    """ Generic class that defines what an endpoint should provide """
    url: str
    name: str

    def collectMetrics(self, metric: Metric) -> Metric:
        return metric

class PingEndpoint(Endpoint):
    def __init__(self, name, baseUrl):
        self.name = name
        self.url = "{}/{}".format(baseUrl, "ping")

    def collectMetrics(self, response: dict, metric: Metric) -> Metric:
        if "status" in response.keys():
            if response["status"] == "pong":
                metric.add_sample(
                    "freqtrade_up",
                    value=float(1),
                    labels={"name":self.name}
                )
            else:
                metric.add_sample(
                    "freqtrade_up",
                    value=0.0,
                    labels={"name":self.name}
                )
        return metric

class ProfitEndpoint(Endpoint):
    def __init__(self, name, baseUrl):
        self.name = name
        self.url = "{}/{}".format(baseUrl, "profit")

    def collectMetrics(self, response:dict, metric:Metric) -> Metric:
        for key in response.keys():
            freqtrademetric = "_".join(["freqtrade", key])
            if response[key] is not None:
                try:
                    metric.add_sample(
                        freqtrademetric,
                        value=float(response[key]),
                        labels={"name":self.name}
                    )
                except Exception:
                    pass
        return metric

class StatusEndpoint(Endpoint):
    def __init__(self, name, baseUrl):
        self.name = name
        self.url = "{}/{}".format(baseUrl, "status")

    def collectMetrics(self, data:dict, metric:Metric) -> Metric:
        for trade in data:
            for key in ["trade_id",
                        "amount",
                        "stake_amount",
                        "fee_open_cost",
                        "open_timestamp",
                        "open_rate",
                        "open_rate_requested",
                        "open_trade_value",
                        "profit_ratio",
                        "profit_pct",
                        "profit_abs",
                        "stop_loss_abs",
                        "stop_loss_ratio",
                        "stop_loss_pct",
                        "stoploss_last_update_timestamp",
                        "initial_stop_loss_abs",
                        "initial_stop_loss_ratio",
                        "initial_stop_loss_pct",
                        "min_rate",
                        "max_rate",
                        "open_order_id",
                        "stoploss_current_dist",
                        "stoploss_current_dist_pct",
                        "stoploss_current_dist_ratio",
                        "stoploss_entry_dist",
                        "stoploss_entry_dist_ratio",
                        "current_profit",
                        "current_profit_abs",
                        "current_profit_pct",
                        "current_rate"]:
                freqtrademetric = "_".join(["freqtrade_status", key])
                try:
                    metric.add_sample(
                        freqtrademetric,
                        value=float(trade[key]),
                        labels={"name":self.name, "pair":trade["pair"], "strategy":trade["strategy"]}
                    )
                except Exception:
                    pass
        return metric

class Bot:
    """ asdfasd"""
    url = str
    name = str
    headers = dict
    formatters = dict
    access_token = str
    refresh_token = str
    connection_retry_counter = 0
    endpoints = []

    def __init__(self, url, name):
        self.name = name

        self.url = "http://"+url+"/api/v1"
        self.endpoints = []

        try:
            response = requests.request("POST",
                    self.url + "/token/login",
                    headers = {
                      'Authorization': 'Basic ZnJlcXRyYWRlcjpTdXBlclNlY3VyZVBhc3N3b3Jk'
                    },
                    data={}
                    )
            log.info("Connected to {}, adding endpoints...".format(self.name))
            self.access_token = response.json()["access_token"]
            self.refresh_token = response.json()["refresh_token"]
            self.headers = {"Authorization": "Bearer "+self.access_token}
            self.endpoints.append(ProfitEndpoint(name=self.name, baseUrl=self.url))
            self.endpoints.append(StatusEndpoint(name=self.name, baseUrl=self.url))
            self.endpoints.append(PingEndpoint(name=self.name, baseUrl=self.url))
        except Exception:
            log.error("Could not create a connection to bot {} under {}, check if its API is running properly".format(self.name, self.url))

    def refreshToken(self):
        url = "{}/token/refresh".format(self.url)
        log.info("Refreshing token for {} over {}".format(self.url, url))
        payload={}
        headers = {
          'Authorization': 'Bearer {}'.format(self.refresh_token)
       }
        response = requests.request("POST", url, headers=headers, data=payload).json()
        self.headers = {
          'Authorization': 'Bearer '+response["access_token"]
       }
    
    def addMetrics(self, metric: Metric) -> Metric:
        """ Adds metrics to main thread Metric object"""
        if not self.access_token:
            # If we dont have an access token yet we retry connecting to the bot...
            # ... if 30 iterations passed
            if self.connection_retry_counter >= 30:
                log.info("Trying again to connect to {}.".format(self.name))
                self.__init__(self.url, self.name)
            else:
                self.connection_retry_counter += 1
        else:    
            for endpoint in self.endpoints:
                #r = None
                #try:
                r = requests.request("GET", endpoint.url, headers=self.headers, data={})
                #except Exception:
                #    log.info("Skipping endpoint {} as we got an exception.".format(endpoint.url))
                #    continue
                #if r:
                if "detail" in r.json() or r.status_code == 401:
                    log.info("Refreshing token as {} has a token timeout".format(self.url))
                    self.refreshToken()
                    r = requests.request("GET", endpoint.url, headers=self.headers, data={})
                metric = endpoint.collectMetrics(r.json(), metric)
        return metric

class Collector:
    """ Collector for running bots """
    def __init__(self):
        self.bots = []
        for url in BOTS.keys():
            # Create a Bot for each name: address pair in global BOTS variable
            self.bots.append(Bot(BOTS[url], url))

    def collect(self):
        # query the api
        metric = Metric("freqtrade", "freqtrade metric values", "gauge")
        for bot in self.bots:
            metric = bot.addMetrics(metric)

        yield metric


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(
            description=__doc__,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        parser.add_argument(
            "--port",
            nargs="?",
            const=3000,
            help="The TCP port to listen on",
            default=3000,
        )
        parser.add_argument(
            "--addr",
            nargs="?",
            const="0.0.0.0",
            help="The interface to bind to",
            default="0.0.0.0",
        )
        args = parser.parse_args()
        log.info("listening on http://%s:%d/metrics" % (args.addr, args.port))

        REGISTRY.register(Collector())
        start_http_server(int(args.port), addr=args.addr)

        while True:
            time.sleep(30)
    except KeyboardInterrupt:
        print("Interrupted.")
        exit(0)
