#!/usr/bin/env python

import gevent.pool
import json
import sys

from geventhttpclient import HTTPClient
from geventhttpclient.url import URL


if __name__ == "__main__":

    url = URL(sys.argv[1])
    
    # setting the concurrency to 10 allow to create 10 connections and
    # reuse them.
    http = HTTPClient.from_url(url, concurrency=10)

    response = http.get(url.request_uri)
    print "status: %s" % response.status_code

    http.close()
    