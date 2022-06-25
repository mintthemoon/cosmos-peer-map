import os
import json
import requests
import sys
import plotly.express as px
import pandas as pd


class Peer:
    api_url = "http://ip-api.com/json/"

    def __init__(self, name, ip):
        self.name = name
        self.ip = ip
        try:
            api_info = requests.get(self.api_url + self.ip).json()
            self.org = api_info["org"]
            self.city = api_info["city"]
            self.country = api_info["country"]
            self.loc = (api_info["lat"], api_info["lon"])
        except Exception as err:
            print(f"failed to map {self.ip} ({self.name})")
            self.loc = None


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
    peers_data = [
        (peer.name, peer.loc[0], peer.loc[1], peer.ip, peer.country, peer.city, peer.org)
        for peer in peers
        if peer.loc
    ]
    peers_df = pd.DataFrame.from_records(
        peers_data, 
        columns=("name", "lat", "lon", "ip", "country", "city", "org")
    )
    fig = px.density_mapbox(
        peers_df,
        hover_name="name",
        hover_data=("ip", "country", "city", "org"),
        lat="lat",
        lon="lon",
        radius=10,
        center={"lat": 40, "lon": -20},
        zoom=2,
        mapbox_style="carto-darkmatter",
    )
    fig.update_layout(title="Cosmos Peer Map", title_x=0.5)
    fig.write_html(html_out)


if __name__ == "__main__":
    main()
