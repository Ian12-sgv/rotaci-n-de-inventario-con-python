# utils/my_sql_detector.py

import socket
import time
import getpass

def get_available_sql_servers(timeout=5):
    """
    Escanea la red por broadcast UDP para descubrir instancias SQL Server.
    Devuelve una lista de strings con formato IP\INSTANCIA o IP si no tiene nombre.
    """
    message = b'\x02'
    broadcast_address = ('255.255.255.255', 1434)
    responses = []

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(timeout)

    try:
        sock.sendto(message, broadcast_address)
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                data, addr = sock.recvfrom(4096)
                response = data.decode(errors='ignore')
                responses.append((addr[0], response))
            except socket.timeout:
                break
    finally:
        sock.close()

    instances = []
    for ip, resp in responses:
        fields = resp.split(";")
        data = dict(zip(fields[::2], fields[1::2]))
        server = data.get("ServerName", "")
        instance = data.get("InstanceName", "")
        if instance and instance.upper() != "MSSQLSERVER":
            instances.append(f"{ip}\\{instance}")
        else:
            instances.append(ip)
    return instances

def get_default_username():
    """
    Retorna el nombre de usuario actual del sistema.
    Útil para autenticación integrada.
    """
    return getpass.getuser()
