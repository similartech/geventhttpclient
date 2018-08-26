#!/usr/bin/env python

from geventhttpclient import HTTPClient, URL

if __name__ == "__main__":

    url = URL('https://www.unibet.co.uk/')
    http = HTTPClient.from_url(url)
    response = http.get(url.request_uri)
    assert response.status_code == 200

    CHUNK_SIZE = 1024 * 16 # 16KB
    data = response.read(CHUNK_SIZE)
    while data:
        print data
        data = response.read(CHUNK_SIZE)


