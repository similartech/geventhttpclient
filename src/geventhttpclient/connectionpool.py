import gevent.queue
import gevent.socket
import ssl
import os

_CA_CERTS = None

try:
    from ssl import get_default_verify_paths
except ImportError:
    _CA_CERTS = None
else:
    _certs = get_default_verify_paths()
    _CA_CERTS = _certs.cafile or _certs.capath

if not _CA_CERTS or os.path.isdir(_CA_CERTS):
    import certifi
    _CA_CERTS = certifi.where()

try:
    from ssl import _DEFAULT_CIPHERS
except ImportError:
    # ssl._DEFAULT_CIPHERS in python2.7 branch.
    # _DEFAULT_CIPHERS = (
    #     'ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:ECDH+HIGH:'
    #     'DH+HIGH:ECDH+3DES:DH+3DES:RSA+AESGCM:RSA+AES:RSA+HIGH:RSA+3DES:ECDH+RC4:'
    #     'DH+RC4:RSA+RC4:!aNULL:!eNULL:!MD5')

    _DEFAULT_CIPHERS = (
        'TLS13-AES-256-GCM-SHA384:TLS13-CHACHA20-POLY1305-SHA256:'
        'TLS13-AES-128-GCM-SHA256:'
        'ECDH+AESGCM:ECDH+CHACHA20:DH+AESGCM:DH+CHACHA20:ECDH+AES256:DH+AES256:'
        'ECDH+AES128:DH+AES:ECDH+HIGH:DH+HIGH:RSA+AESGCM:RSA+AES:RSA+HIGH:'
        '!aNULL:!eNULL:!MD5:!3DES'
        )

try:
    from gevent import lock
except ImportError:
    # gevent < 1.0b2
    from gevent import coros as lock

DEFAULT_CONNECTION_TIMEOUT = 5.0
DEFAULT_NETWORK_TIMEOUT = 5.0

IGNORED = object()


class ConnectionPool(object):

    DEFAULT_CONNECTION_TIMEOUT = 5.0
    DEFAULT_NETWORK_TIMEOUT = 5.0

    def __init__(self, host, port,
            size=5, disable_ipv6=False,
            connection_timeout=DEFAULT_CONNECTION_TIMEOUT,
            network_timeout=DEFAULT_NETWORK_TIMEOUT):
        self._closed = False
        self._host = host
        self._port = port
        self._semaphore = lock.BoundedSemaphore(size)
        self._socket_queue = gevent.queue.LifoQueue(size)
        self._host_ip = ''

        self.connection_timeout = connection_timeout
        self.network_timeout = network_timeout
        self.size = size
        self.disable_ipv6 = disable_ipv6

    @property
    def host_ip(self):
        """ The ip address of the host
        """

        return self._host_ip

    def _resolve(self):
        """ resolve (dns) socket informations needed to connect it.
        """
        family = 0
        if self.disable_ipv6:
            family = gevent.socket.AF_INET
        info = gevent.socket.getaddrinfo(self._host, self._port,
                family, 0, gevent.socket.SOL_TCP)
        # family, socktype, proto, canonname, sockaddr = info[0]
        return info

    def close(self):
        self._closed = True
        while not self._socket_queue.empty():
            try:
                sock = self._socket_queue.get(block=False)
                try:
                    sock.close()
                except:
                    pass
            except gevent.queue.Empty:
                pass

    def _create_tcp_socket(self, family, socktype, protocol):
        """ tcp socket factory.
        """
        sock = gevent.socket.socket(family, socktype, protocol)
        return sock

    def _create_socket(self):
        """ might be overriden and super for wrapping into a ssl socket
            or set tcp/socket options
        """
        sock_infos = self._resolve()

        if sock_infos[0] and sock_infos[0][4] and sock_infos[0][4][0]:
            self._host_ip = sock_infos[0][4][0]

        first_error = None
        for sock_info in sock_infos:
            try:
                sock = self._create_tcp_socket(*sock_info[:3])
            except ssl.SSLError as se:
                self.insecure = True
                sock = self._create_tcp_socket(*sock_info[:3])
            except Exception as e:
                if not first_error:
                    first_error = e
                continue

            try:
                sock.settimeout(self.connection_timeout)
                try:
                    sock.connect(sock_info[-1])
                except ssl.SSLError as se:
                    self.insecure = True
                    sock = self._create_tcp_socket(*sock_info[:3])
                    sock.settimeout(self.connection_timeout)
                    sock.connect(sock_info[-1])
                self.after_connect(sock)
                sock.settimeout(self.network_timeout)
                return sock
            except IOError as e:
                sock.close()
                if not first_error:
                    first_error = e
            except:
                sock.close()
                raise

        if first_error:
            raise first_error
        else:
            raise RuntimeError("Cannot resolve %s:%s" % (self._host, self._port))

    def after_connect(self, sock):
        pass

    def get_socket(self):
        """ get a socket from the pool. This blocks until one is available.
        """
        self._semaphore.acquire()
        if self._closed:
            raise RuntimeError('connection pool closed')
        try:
            return self._socket_queue.get(block=False)
        except gevent.queue.Empty:
            try:
                return self._create_socket()
            except:
                self._semaphore.release()
                raise

    def return_socket(self, sock):
        """ return a socket to the pool.
        """
        if self._closed:
            try:
                sock.close()
            except:
                pass
            return
        self._socket_queue.put(sock)
        self._semaphore.release()

    def release_socket(self, sock):
        """ call when the socket is no more usable.
        """
        try:
            sock.close()
        except:
            pass
        if not self._closed:
            self._semaphore.release()


try:
    import gevent.ssl
    try:
        from gevent.ssl import match_hostname
    except ImportError:
        from backports.ssl_match_hostname import match_hostname
except ImportError:
    pass
else:
    class SSLConnectionPool(ConnectionPool):
        """ SSLConnectionPool creates connections wrapped with SSL/TLS.

        :param host: hostname
        :param port: port
        :param ssl_options: accepts any options supported by `ssl.wrap_socket`
        :param ssl_context_factory: use `ssl.create_default_context` by default
            if provided. It must be a callbable that returns a SSLContext.
        """

        default_options = {
            'ciphers': _DEFAULT_CIPHERS,
            'ca_certs': _CA_CERTS,
            'cert_reqs': gevent.ssl.CERT_REQUIRED
        }

        ssl_context_factory = getattr(gevent.ssl, "create_default_context", None)

        def __init__(self, host, port, **kw):
            self.ssl_options = kw.pop("ssl_options", {})
            self.ssl_context_factory = kw.pop('ssl_context_factory', None)
            self.insecure = kw.pop('insecure', False)
            self.dont_validate_certificate = kw.pop('dont_validate_certificate', False)

            super(SSLConnectionPool, self).__init__(host, port, **kw)

        def after_connect(self, sock):
            super(SSLConnectionPool, self).after_connect(sock)

            if not self.insecure and not self.dont_validate_certificate:
                match_hostname(sock.getpeercert(), self._host)

        def _create_tcp_socket(self, family, socktype, protocol):
            sock = super(SSLConnectionPool, self)._create_tcp_socket(
                family, socktype, protocol)

            if self.insecure:
                self.ssl_options = {}

            if self.ssl_context_factory is None:
                ssl_options = self.default_options.copy()
                ssl_options.update(self.ssl_options)
                ssl_options = {}
                if not self.insecure:
                    ssl_options = self.default_options.copy()
                    ssl_options.update(self.ssl_options)
                return gevent.ssl.wrap_socket(sock, **ssl_options)
            else:
                return self.ssl_context_factory().wrap_socket(sock, **self.ssl_options)
