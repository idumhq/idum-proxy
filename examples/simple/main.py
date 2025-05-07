from idum_proxy import IdumProxy

if __name__ == "__main__":
    idum_proxy: IdumProxy = IdumProxy(config_file="proxy.json")
    idum_proxy.serve(host="0.0.0.0", port=8091)
