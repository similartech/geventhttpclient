FROM docker-st-alpine-py2-deps-dev
MAINTAINER Yaniv Hadad <yaniv@similartech.com>

ENV GEVENT_RESOLVER ares
ENV PYTHON_DIR /opt/similartech/python
ENV DEPLOYMENT_DIR $PYTHON_DIR/py-st-geventhttpclient

ADD . $DEPLOYMENT_DIR

RUN echo \
  && cd $DEPLOYMENT_DIR \
  && make develop \
  && echo

WORKDIR $DEPLOYMENT_DIR
CMD [ "python" ]