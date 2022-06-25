import os
import json
import folium
import requests
from geoip import geolite2

def main():
    rpc_url = os.environ.get("RPC_URL", "http://localhost:26657")
    net_info_response = requests.get(rpc_url + "/net_info")
    net_info_response.raise_for_status()
    net_info = net_info_response.json()
    if "result" not in net_info:
        raise RuntimeError("invalid rpc response")
    ips = {
        peer["node_info"]["moniker"]: peer["remote_ip"]
        for peer in net_info["result"]["peers"]
    }
    lookups = {moniker: geolite2.lookup(ip) for moniker, ip in ips.items()}
    coordinates = {
        moniker: lookup.location 
        for moniker, lookup in lookups.items() 
        if lookup
    }
    peer_map = folium.Map(location=(20.0, -40.0), zoom_start=3)
    markers = [
        folium.Marker(loc, popup=moniker).add_to(peer_map)
        for moniker, loc in coordinates.items()
    ]
    print(peer_map._repr_html_())

if __name__ == "__main__":
    main()