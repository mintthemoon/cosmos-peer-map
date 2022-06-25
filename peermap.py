import os
import json
import requests
from geoip import geolite2
import sys
import plotly.express as px
import pandas as pd


class Peer:
    def __init__(self, name, ip):
        self.name = name
        self.ip = ip
        self.location = locate_ip(ip)


def locate_ip(ip):
    location_info = geolite2.lookup(ip)
    return location_info.location if location_info else None


def main():
    if len(sys.argv) < 2:
        raise RuntimeError("usage: peermap.py <html_out>")
    html_out = sys.argv[1]
    rpc_url = os.environ.get("RPC_URL", "http://localhost:26657")
    net_info_response = requests.get(rpc_url + "/net_info")
    net_info_response.raise_for_status()
    net_info = net_info_response.json()
    if "result" not in net_info:
        raise RuntimeError("invalid rpc response")
    peers = [
        Peer(name=peer["node_info"]["moniker"], ip=peer["remote_ip"])
        for peer in net_info["result"]["peers"]
    ]
    coordinates = {peer.name: peer.location for peer in peers if peer.location}
    df = pd.DataFrame.from_dict(coordinates, orient="index", columns=["lat", "long"])
    fig = px.density_mapbox(
        df,
        lat="lat",
        lon="long",
        radius=10,
        center=dict(lat=0, lon=90),
        zoom=1,
        mapbox_style="carto-darkmatter",
    )
    fig.update_layout(title="Cosmos Peer Map", title_x=0.5)
    fig.write_html(html_out)


if __name__ == "__main__":
    main()
