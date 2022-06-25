# cosmos-peer-map
generate an html map of connected peers based on geoip data.

the html output can be viewed in a web browser.

## usage
install dependencies:
```
python3 -m pip install -r requirements.txt
```

run with local rpc:
```
python3 peermap.py > peers.html
```

run with remote rpc:
```
RPC_URL=<url> python3 peermap.py > peermap.html
```

## notes
uses geolite2 for data which is a free API, you may hit request limits running too many times from one device.