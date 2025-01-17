"""
start_client
============
Starts qickdawg pyro client or locally

"""

import Pyro4
from qick import QickConfig
import qickdawg as qd


def start_client(host_ip_address=None, host_port=8888, server_name="myqick", *arg, **kwarg):
    """Start qick client and return remote socket and configurations

    Parameters
    ----------
    host_ip_address: str (default None)
        If None, connects in local mode
        Otherwise, connect to pyro server
    host_port: int (default 8888)
    server_name: str (default "myqick")

    """
    if host_ip_address is not None:
        Pyro4.config.SERIALIZER = "pickle"
        Pyro4.config.PICKLE_PROTOCOL_VERSION = 4

        ns_host = host_ip_address
        ns_port = 8888
        server_name = server_name

        ns = Pyro4.locateNS(host=ns_host, port=ns_port)
        qd.soc = Pyro4.Proxy(ns.lookup(server_name))
        qd.soccfg = QickConfig(qd.soc.get_cfg())
    else:
        from qick import QickSoc
        qd.soc = QickSoc(*arg, **kwarg)
        qd.soccfg = qd.soc

    qd.max_int_time_tus = qd.soc.cycles2us(2 ** 16 - 1)
    qd.max_int_time_tns = qd.soc.cycles2us(2 ** 16 - 1) * 1000
    qd.max_int_time_treg = 2 ** 16 - 1

    qd.min_time_tus = qd.soc.cycles2us(1)
    qd.min_time_tns = qd.soc.cycles2us(1) * 1000
