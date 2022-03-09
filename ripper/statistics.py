import threading
import sys
import time
import _thread
from datetime import datetime
from ripper.context import Context
from ripper.common import convert_size, print_logo, get_first_ip_part, get_no_successful_connection_die_msg
from ripper.constants import DEFAULT_CURRENT_IP_VALUE, HOST_FAILED_STATUS, HOST_SUCCESS_STATUS
import ripper.services
from ripper.health_check import construct_request_url

lock = threading.Lock()


def get_health_status(_ctx: Context):
    if(_ctx.last_host_statuses_update is None or len(_ctx.host_statuses.values()) == 0):
        return f'...detecting ({_ctx.health_check_method.upper()} health check method)'

    failed_cnt = 0
    succeeded_cnt = 0
    if HOST_FAILED_STATUS in _ctx.host_statuses:
        failed_cnt = _ctx.host_statuses[HOST_FAILED_STATUS]
    if HOST_SUCCESS_STATUS in _ctx.host_statuses:
        succeeded_cnt = _ctx.host_statuses[HOST_SUCCESS_STATUS]

    total_cnt = failed_cnt + succeeded_cnt
    if total_cnt < 1:
        return
    
    availability_percentage = round(100 * succeeded_cnt / total_cnt)
    if(availability_percentage < 50):
        return f'Accessible in {succeeded_cnt} of {total_cnt} zones ({availability_percentage}%). It should be dead. Consider another target!'
    else:
        return f'Accessible in {succeeded_cnt} of {total_cnt} zones ({availability_percentage}%)'


def format_dt(dt: datetime):
    if dt is None:
        return ''
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def show_info(_ctx: Context):
    """Prints attack info to console."""
    print("\033c")
    print_logo()

    my_ip_masked = get_first_ip_part(_ctx.current_ip) if _ctx.current_ip != DEFAULT_CURRENT_IP_VALUE \
        else DEFAULT_CURRENT_IP_VALUE
    is_random_packet_len = _ctx.attack_method in ('tcp', 'udp') and _ctx.random_packet_len

    if _ctx.current_ip:
        if _ctx.current_ip == _ctx.start_ip:
            your_ip = my_ip_masked
        else:
            your_ip = f'IP was changed, check VPN (current IP: {my_ip_masked})'
    else:
        your_ip = f'Can\'t get your IP. Check internet connection.'

    target_host = f'{_ctx.original_host}:{_ctx.port}'
    load_method = f'{str(_ctx.attack_method).upper()}'
    thread_pool = f'{_ctx.threads}'
    available_cpu = f'{_ctx.cpu_count}'
    rnd_packet_len = 'YES' if is_random_packet_len else 'NO'
    max_rnd_packet_len = f'{_ctx.max_random_packet_len}' if is_random_packet_len else 'NOT REQUIRED'
    ddos_protection = 'Protected' if _ctx.isCloudflareProtected else 'Not protected'

    print('-----------------------------------------------------------')
    print(f'Start time:                   {format_dt(_ctx.start_time)}')
    print(f'Your public IP:               {your_ip} / {_ctx.my_country}')
    print(f'Host:                         {target_host} / {_ctx.target_country}')
    print(f'Host availability:            {get_health_status(_ctx)}')
    if _ctx.last_host_statuses_update is not None:
        print(f'Host availability updated at: {format_dt(_ctx.last_host_statuses_update)}')
    print(f'CloudFlare Protection:        {ddos_protection}')
    print(f'Load Method:                  {load_method}')
    print(f'Threads:                      {thread_pool}')
    print(f'vCPU count:                   {available_cpu}')
    print(f'Random Packet Length:         {rnd_packet_len}')
    print(f'Max Random Packet Length:     {max_rnd_packet_len}')
    print('-----------------------------------------------------------')

    sys.stdout.flush()


def show_statistics(_ctx: Context):
    """Prints statistics to console."""
    if not _ctx.show_statistics:
        _ctx.show_statistics = True

        lock.acquire()
        if not _ctx.getting_ip_in_progress:
            t = threading.Thread(target=ripper.services.update_current_ip, args=[_ctx])
            t.start()
            t = threading.Thread(target=ripper.services.update_host_statuses, args=[_ctx])
            t.start()
        lock.release()

        if _ctx.attack_method == 'tcp':
            attack_successful = ripper.services.check_successful_tcp_attack(_ctx)
        else:
            attack_successful = ripper.services.check_successful_connections(_ctx)
        if not attack_successful:
            print(f"\n\n\n{get_no_successful_connection_die_msg()}")
            _thread.interrupt_main()
            exit()

        # cpu_load = get_cpu_load()

        show_info(_ctx)

        connections_success = f'{_ctx.connections_success}'
        connections_failed = f'{_ctx.connections_failed}'

        curr_time = datetime.now() - _ctx.start_time

        print(f'Duration:                     {str(curr_time).split(".", 2)[0]}')
        # print(f'CPU Load Average:             {cpu_load}')
        if _ctx.attack_method == 'http':
            print(f'Requests sent:                {_ctx.packets_sent}')
            if len(_ctx.http_codes_counter.keys()):
                print(f'HTTP codes distribution:      {build_http_codes_distribution(_ctx.http_codes_counter)}')
        elif _ctx.attack_method == 'tcp':
            size_sent = convert_size(_ctx.packets_sent)
            if _ctx.packets_sent == 0:
                size_sent = f'{size_sent}'
            else:
                size_sent = f'{size_sent}'

            print(f'Total Packets Sent Size:      {size_sent}')
        else:  # udp
            print(f'Packets Sent:                 {_ctx.packets_sent}')
        print(f'Connection Success:           {connections_success}')
        print(f'Connection Failed:            {connections_failed}')
        print('-----------------------------------------------------------')
        print(f'Press CTRL+C to interrupt process.')

        if _ctx.errors:
            print('\n\n')
        for error in _ctx.errors:
            print(f'{error}')
            print('\007')

        sys.stdout.flush()
        time.sleep(3)
        _ctx.show_statistics = False


def build_http_codes_distribution(http_codes_counter):
    codes_distribution = []
    total = sum(http_codes_counter.values())
    for code in http_codes_counter.keys():
        count = http_codes_counter[code]
        percent = round(count * 100 / total)
        codes_distribution.append(f'{code}: {count} ({percent}%)')
    return ', '.join(codes_distribution)
