from mininet import topo


class LinearTopo(topo.LinearTopo):

    def __init__(self, params, linkopts):
        self.params = params
        # topo.LinearTopo.__init__(self, self.params["num_switches"], self.params["num_hosts_per_switch"])
        topo.LinearTopo.__init__(self, self.params["num_switches"],
                                 self.params["num_hosts_per_switch"], **linkopts)

    def __str__(self):
        params_str = ''
        for k, v in self.params.items():
            params_str += "_" + str(k) + "_" + str(v)
        return self.__class__.__name__ + params_str
