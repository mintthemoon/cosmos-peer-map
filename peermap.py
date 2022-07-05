import os
import sys
import json
import redis
import logging
import requests
import pandas as pd
import plotly.express as px
from flask import Flask

class PeerMap:
    peers_frame_cols = ("name", "lat", "lon", "ip", "country", "city", "org")

    def __init__(self, rpc):
        log.info("creating peer map for %s", rpc.url)
        self.rpc = rpc
        self.peers = rpc.located_peers
        self.peers_data = [peer.get_data() for peer in self.peers]
        self.peers_frame = pd.DataFrame.from_records(self.peers_data, columns=self.peers_frame_cols)
        self.figure = px.density_mapbox(
            self.peers_frame,
            hover_name="name",
            hover_data=("ip", "country", "city", "org"),
            lat="lat",
            lon="lon",
            radius=10,
            center={"lat": 20, "lon": 0},
            zoom=1.5,
            mapbox_style="carto-darkmatter",
        )
        self.figure.update_layout(title="Cosmos Peer Map", title_x=0.5)
        log.info("created peer map for %s", rpc.url)


class RPC:
    cache_ttl_seconds = 300

    def __init__(self, url):
        self.url = url
        log.debug("mapping peers")
        self.peers = self.get_peers()
        self.located_peers = [peer for peer in self.peers if peer.loc]
        log.debug("mapped %d peers", len(self.located_peers))

    def get_peers(self):
        cache_info = db.get(f"rpc-{self.url}") if db else None
        if cache_info:
            log.info("using cached peer list for %s", self.url)
            net_info = json.loads(cache_info)
        else:
            log.info("requesting peer list from %s", self.url)
            net_info_response = requests.get(self.url + "/net_info")
            net_info_response.raise_for_status()
            net_info = net_info_response.json()
            if db:
                db.set(f"rpc-{self.url}", net_info_response.content)
                db.expire(f"rpc-{self.url}", self.cache_ttl_seconds)
        return [
            Peer(name=peer["node_info"]["moniker"], ip=peer["remote_ip"])
            for peer in net_info["result"]["peers"]
        ]
        


class Peer:
    api_url = "http://ip-api.com/json/"

    def __init__(self, name, ip):
        self.name = name
        self.ip = ip
        api_info = self.get_api_info()
        if api_info:
            self.org = api_info["org"]
            self.city = api_info["city"]
            self.country = api_info["country"]
            self.loc = (api_info["lat"], api_info["lon"])
        else:            
            log.warning("failed to map %s (%s)", self.ip, self.name)
            self.loc = None
    
    def get_api_info(self):
        cache_info = db.get(f"peer-{self.ip}") if db else None
        if cache_info:
            log.debug("cache hit: %s", self.name)
            api_info = json.loads(cache_info)
        else:
            try:
                log.debug("cache miss: %s", self.name)
                api_response = requests.get(self.api_url + self.ip)
                api_response.raise_for_status()
                if db:
                    db.set(f"peer-{self.ip}", api_response.content)
                api_info = api_response.json()
            except Exception as err:
                log.warning("api error: %s", self.name)
                api_info = None
        return api_info

    def get_data(self):
        return (self.name, self.loc[0], self.loc[1], self.ip, self.country, self.city, self.org)


if os.environ.get("DEBUG") in ("1", "true"):
    loglevel = logging.DEBUG
else:
    loglevel = logging.INFO
logging.basicConfig(format="[%(asctime)s] %(levelname)s: %(message)s", level=loglevel)
log = logging.getLogger()
rpc_url = os.environ.get("RPC_URL", "http://localhost:26657")
if os.environ.get("CACHE") not in ("0", "false"):
    redis_host = os.environ.get("REDIS_HOST", "localhost")
    redis_port = os.environ.get("REDIS_PORT", 6379)
    RPC.cache_ttl_seconds = int(os.environ.get("RPC_CACHE_TTL_SECONDS", 300))
    log.info("connecting to redis at %s:%d", redis_host, redis_port)
    log.debug("rpc cache ttl: %d seconds", RPC.cache_ttl_seconds)
    db = redis.Redis(host=redis_host, port=redis_port)
else:
    log.info("skipping cache initialization")
    db = None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise RuntimeError("usage: peermap.py <html_out>")
    html_out = sys.argv[1]
    rpc = RPC(url=rpc_url)
    peermap = PeerMap(rpc=rpc)
    peermap.figure.write_html(html_out)
    sys.exit(0)

app = Flask(__name__)
log = app.logger

@app.route('/')
def index():
    rpc = RPC(url=rpc_url)
    peermap = PeerMap(rpc=rpc)
    return peermap.figure.to_html()
