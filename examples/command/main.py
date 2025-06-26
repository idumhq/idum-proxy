from idum_proxy import IdumProxy

if __name__ == "__main__":
    # Initialize the proxy
    idum_proxy: IdumProxy = IdumProxy(config_file="proxy.json")
    idum_proxy.serve()
    """
    # Start proxy in a separate daemon thread
    proxy_thread = threading.Thread(
        target=idum_proxy.serve, daemon=True, name="IdumProxyThread"
    )


    def wait_port_available(host: str, port: int):
        def _socket_test_connection():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1)  # Add timeout to avoid blocking indefinitely
                result = s.connect_ex((host, port))
                s.close()
                return result == 0  # 0 means connection successful
            except Exception:
                return False

        while _socket_test_connection():
            logging.info(f"waiting for port {port}")
            time.sleep(1)


    def check_port_available(host: str, port: int):
        def _socket_test_connection():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1)  # Add timeout to avoid blocking indefinitely
                result = s.connect_ex((host, port))
                s.close()
                return result == 1
            except Exception:
                return True

        while _socket_test_connection():
            logging.info(f"port {port} is not available")
            time.sleep(1)


    check_port_available(host="0.0.0.0", port=8080)
    proxy_thread.start()
    wait_port_available(host="0.0.0.0", port=8080)
    """
