#!/usr/bin/env python

import gevent.pool
import json

from geventhttpclient import HTTPClient
from geventhttpclient.url import URL


if __name__ == "__main__":

    url = URL('https://www.similartech.com')
    
    # setting the concurrency to 10 allow to create 10 connections and
    # reuse them.
    http = HTTPClient.from_url(url, concurrency=10)

    response = http.get(url.request_uri)
    assert response.status_code == 200

    http.close()
