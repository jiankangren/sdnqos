#__author__ = 'Rakesh Kumar, Monowar Hasan'

import time
import os
import json
import httplib2
import fcntl
import struct
from socket import *

from collections import defaultdict
from functools import partial
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.node import OVSSwitch
from mininet.link import TCIntf, TCLink

from mininet.util import custom
from model.network_graph import NetworkGraph
from model.network_graph import NetworkGraphLinkData

from model.match import Match

from experiments.topologies.ring_topo import RingTopo
from experiments.topologies.clos_topo import ClosTopo
from experiments.topologies.linear_topo import LinearTopo
from experiments.topologies.fat_tree import FatTree
from experiments.topologies.two_ring_topo import TwoRingTopo
from experiments.topologies.ring_line_topo import RingLineTopo
from experiments.topologies.clique_topo import CliqueTopo
from experiments.topologies.ameren_topo import AmerenTopo
# mhasan import : ring
from experiments.topologies.ring_topo_with_param import RingTopoWithParams
from experiments.topologies.random_topo_with_param import RandomTopoWithParams

from synthesis.dijkstra_synthesis import DijkstraSynthesis
from synthesis.aborescene_synthesis import AboresceneSynthesis
from synthesis.synthesize_qos import SynthesizeQoS
from synthesis.synthesis_lib import SynthesisLib

# mhasan import: networkx
import networkx as nx
import sys
# from mcp_helper import MCP_Helper
import random

class NetworkConfiguration(object):

    def __init__(self, controller,
                 topo_name,
                 topo_params,
                 conf_root,
                 synthesis_name,
                 synthesis_params,
                 flow_specs,
                 # mhasan: added link param in constructor
                 topo_link_params,
                 number_of_RT_flows,
                 number_of_BE_flows,
                 test_case_id
                 ):

        self.controller = controller
        self.topo_name = topo_name
        self.topo_params = topo_params
        self.topo_name = topo_name
        self.conf_root = conf_root
        self.synthesis_name = synthesis_name
        self.synthesis_params = synthesis_params
        self.flow_specs = flow_specs
        # mhasan: added link param
        self.topo_link_params = topo_link_params

        self.number_of_RT_flows = number_of_RT_flows
        self.number_of_BE_flows = number_of_BE_flows

        self.controller_port = 6633
        self.topo = None
        self.nc_topo_str = None
        self.init_topo()
        self.init_synthesis()

        self.mininet_obj = None
        self.ng = None

        self.test_case_id = test_case_id

        self.isFeasible = True

        self.min_delay_budget_for_all_flows = None  # will update later
        self.network_diameter = None  # will update later

        # Setup the directory for saving configs, check if one does not exist,
        # if not, assume that the controller, mininet and rule synthesis needs to be triggered.
        self.conf_path = self.conf_root + str(self) + "/"
        if not os.path.exists(self.conf_path):
            os.makedirs(self.conf_path)
            self.load_config = False
            self.save_config = True
        else:
            self.load_config = True
            self.save_config = False

        #
        # self.load_config = False
        # self.save_config = True


        # Initialize things to talk to controller
        self.baseUrlRyu = "http://localhost:8080/"

        self.h = httplib2.Http(".cache")
        self.h.add_credentials('admin', 'admin')

        #mhasan : added path
        self.path = None

    def __str__(self):
        return self.controller + "_" + str(self.synthesis) + "_" + str(self.topo) + "_" + str(
            self.number_of_RT_flows) + "_" + str(self.test_case_id)

    def init_topo(self):
        # mhasan : added ring topo with param
        if self.topo_name == "ring_with_param":
            # mhasan: create topo with link param
            self.topo = RingTopoWithParams(self.topo_params, self.topo_link_params)
            self.nc_topo_str = "Ring topology with " + str(self.topo.total_switches) + " switches"
        elif self.topo_name == "random_with_param":
            # mhasan: create topo with link param
            self.topo = RandomTopoWithParams(self.topo_params, self.topo_link_params)
            self.nc_topo_str = "Random topology with " + str(self.topo.total_switches) + " switches"
        elif self.topo_name == "ring":
            # self.topo = RingTopo(self.topo_params)
            # mhasan: create topo with link param
            self.topo = RingTopo(self.topo_params)
            self.nc_topo_str = "Ring topology with " + str(self.topo.total_switches) + " switches"
        elif self.topo_name == "clostopo":
            self.topo = ClosTopo(self.topo_params)
            self.nc_topo_str = "Clos topology with " + str(self.topo.total_switches) + " switches"
        elif self.topo_name == "linear":
            # self.topo = LinearTopo(self.topo_params)
            # mhasan: create topo with link param
            self.topo = LinearTopo(self.topo_params, self.topo_link_params)
            self.nc_topo_str = "Linear topology with " + str(self.topo_params["num_switches"]) + " switches"
        else:
            raise NotImplementedError("Topology: %s" % self.topo_name)

    def init_synthesis(self):
        if self.synthesis_name == "DijkstraSynthesis":
            self.synthesis_params["master_switch"] = self.topo_name == "linear"
            self.synthesis = DijkstraSynthesis(self.synthesis_params)

        elif self.synthesis_name == "SynthesizeQoS":
            self.synthesis = SynthesizeQoS(self.synthesis_params)

        elif self.synthesis_name == "AboresceneSynthesis":
            self.synthesis = AboresceneSynthesis(self.synthesis_params)


    def test_synthesis(self):

        self.mininet_obj.pingAll()

        # is_bi_connected = self.is_bi_connected_manual_ping_test_all_hosts()

        # is_bi_connected = self.is_bi_connected_manual_ping_test([(self.mininet_obj.get('h11'), self.mininet_obj.get('h31'))])

        # is_bi_connected = self.is_bi_connected_manual_ping_test([(self.mininet_obj.get('h31'), self.mininet_obj.get('h41'))],
        #                                                            [('s1', 's2')])
        # print "is_bi_connected:", is_bi_connected

    def get_ryu_switches(self):
        ryu_switches = {}
        request_gap = 0

        # Get all the ryu_switches from the inventory API
        remaining_url = 'stats/switches'
        time.sleep(request_gap)
        resp, content = self.h.request(self.baseUrlRyu + remaining_url, "GET")

        ryu_switch_numbers = json.loads(content)

        for dpid in ryu_switch_numbers:

            this_ryu_switch = {}

            # Get the flows
            remaining_url = 'stats/flow' + "/" + str(dpid)
            resp, content = self.h.request(self.baseUrlRyu + remaining_url, "GET")
            time.sleep(request_gap)

            if resp["status"] == "200":
                switch_flows = json.loads(content)
                switch_flow_tables = defaultdict(list)
                for flow_rule in switch_flows[str(dpid)]:
                    switch_flow_tables[flow_rule["table_id"]].append(flow_rule)
                this_ryu_switch["flow_tables"] = switch_flow_tables
            else:
                print "Error pulling switch flows from RYU."

            # Get the ports
            remaining_url = 'stats/portdesc' + "/" + str(dpid)
            resp, content = self.h.request(self.baseUrlRyu + remaining_url, "GET")
            time.sleep(request_gap)

            if resp["status"] == "200":
                switch_ports = json.loads(content)
                this_ryu_switch["ports"] = switch_ports[str(dpid)]
            else:
                print "Error pulling switch ports from RYU."

            # Get the groups
            remaining_url = 'stats/groupdesc' + "/" + str(dpid)
            resp, content = self.h.request(self.baseUrlRyu + remaining_url, "GET")
            time.sleep(request_gap)

            if resp["status"] == "200":
                switch_groups = json.loads(content)
                this_ryu_switch["groups"] = switch_groups[str(dpid)]
            else:
                print "Error pulling switch ports from RYU."

            ryu_switches[dpid] = this_ryu_switch

        with open(self.conf_path + "ryu_switches.json", "w") as outfile:
            json.dump(ryu_switches, outfile)

    def get_host_nodes(self):

        mininet_host_nodes = {}

        for sw in self.topo.switches():
            mininet_host_nodes[sw] = []
            for h in self.get_all_switch_hosts(sw):
                mininet_host_dict = {"host_switch_id": "s" + sw[1:],
                                     "host_name": h.name,
                                     "host_IP": h.IP(),
                                     "host_MAC": h.MAC()}

                mininet_host_nodes[sw].append(mininet_host_dict)

        with open(self.conf_path + "mininet_host_nodes.json", "w") as outfile:
            json.dump(mininet_host_nodes, outfile)

        return mininet_host_nodes

    def get_links(self):

        mininet_port_links = {}

        with open(self.conf_path + "mininet_port_links.json", "w") as outfile:
            json.dump(self.topo.ports, outfile)

        return mininet_port_links

    # mhasan : for different params in different links
    def get_link_params(self):

        mininet_link_params = self.topo.link_params

        with open(self.conf_path + "mininet_link_params.json", "w") as outfile:
            json.dump(mininet_link_params, outfile)

        return mininet_link_params

    def get_switches(self):
        # Now the output of synthesis is carted away
        if self.controller == "ryu":
            self.get_ryu_switches()
        else:
            raise NotImplemented

    def init_flow_specs(self):
        for fs in self.flow_specs:
            fs.ng_src_host = self.ng.get_node_object(fs.src_host_id)
            fs.ng_dst_host = self.ng.get_node_object(fs.dst_host_id)

            if self.mininet_obj:
                fs.mn_src_host = self.mininet_obj.getNodeByName(fs.src_host_id)
                fs.mn_dst_host = self.mininet_obj.getNodeByName(fs.dst_host_id)

    def setup_network_graph(self, mininet_setup_gap=None, synthesis_setup_gap=None):

        self.start_mininet()
        if mininet_setup_gap:
            time.sleep(mininet_setup_gap)

        # These things are needed by network graph...
        self.get_host_nodes()
        self.get_links()

        # mhasan : for link params
        self.get_link_params()

        self.get_switches()

        self.ng = NetworkGraph(network_configuration=self)
        self.ng.parse_network_graph()

        # Now the synthesis...
        if synthesis_setup_gap:
            time.sleep(synthesis_setup_gap)

        # Refresh just the switches in the network graph, post synthesis
        self.get_switches()
        self.ng.parse_switches()

        # TODO: Figure out a new home for these two
        self.synthesis.network_graph = self.ng
        self.synthesis.mininet_obj = self.mininet_obj
        self.synthesis.synthesis_lib = SynthesisLib("localhost", "8181", self.ng)

        return self.ng

    def get_random_link_data(self, node1, node2):

        delay = int(self.topo_link_params["delay"].replace('us', ''))
        delay = random.randint(delay / 5, delay)  # get a random delay
        link_data = NetworkGraphLinkData(node1, None, node2,
                                         None, None,
                                         self.topo_link_params['bw'] * 1000000,  # in BPS
                                         # convert to float and microsecond to second
                                         float(delay) * 0.000001)
        return link_data

    def setup_network_graph_without_mininet(self):
        #TODO

        nw_graph = nx.Graph()
        switch_names = []

        # setup the switchs
        for i in xrange(self.topo_params["num_switches"]):
            nw_graph.add_node("s" + str(i+1))
            switch_names.append("s" + str(i+1))
            # add hosts per switch
            for j in xrange(self.topo_params["num_hosts_per_switch"]):
                nw_graph.add_node("h" + str(i+1) + str(j+1))

                # add link
                link_data = self.get_random_link_data("s" + str(i+1), "h" + str(i+1) + str(j+1))
                nw_graph.add_edge("s" + str(i + 1),
                                  "h" + str(i + 1) + str(j + 1),
                                  link_data=link_data)

        #  Add links between switches
        if self.topo_params["num_switches"] > 1:
            for i in xrange(self.topo_params["num_switches"] - 1):
                link_data = self.get_random_link_data(switch_names[i], switch_names[i+1])
                nw_graph.add_edge(switch_names[i], switch_names[i+1],
                                  link_data=link_data)

            #  Form a ring only when there are more than two switches
            if self.topo_params["num_switches"] > 2:
                link_data = self.get_random_link_data(switch_names[0], switch_names[-1])
                nw_graph.add_edge(switch_names[0], switch_names[-1],
                                  link_data=link_data)

                # create some random links
                nodelist = self.noncontiguoussample(self.topo_params["num_switches"] - 1,
                                                    int(self.topo_params["num_switches"] / 2.0))

                for i in range(len(nodelist) - 1):
                    switch_names[nodelist[i]]

                    link_data = self.get_random_link_data(switch_names[nodelist[i]], switch_names[nodelist[i + 1]])

                    nw_graph.add_edge(switch_names[nodelist[i]], switch_names[nodelist[i + 1]],
                                      link_data=link_data)



        # print 'adjacency matrix'
        # nx.write_adjlist(nw_graph, sys.stdout)  # write adjacency list to screen
        # print 'end adjacency matrix'

        # print nw_graph.edges(data=True)

        self.ng = NetworkGraph(network_configuration=self)
        self.ng.graph = nw_graph

        return self.ng

    def noncontiguoussample(self, n, k):
        # How many numbers we're not picking
        total_skips = n - k

        # Distribute the additional skips across the range
        skip_cutoffs = random.sample(range(total_skips + 1), k)
        skip_cutoffs.sort()

        # Construct the final set of numbers based on our skip distribution
        samples = []
        for index, skip_spot in enumerate(skip_cutoffs):
            # This is just some math-fu that translates indices within the
            # skips to values in the overall result.
            samples.append(1 + index + skip_spot)

        return samples

    def start_mininet(self):

        self.cleanup_mininet()

        intf = custom(TCIntf, bw=1000)

        self.mininet_obj = Mininet(topo=self.topo,
                                   intf=TCIntf,
                                   link=TCLink,
                                   cleanup=True,
                                   autoStaticArp=True,
                                   controller=lambda name: RemoteController(name, ip='127.0.0.1',
                                                                            port=self.controller_port),
                                   switch=partial(OVSSwitch, protocols='OpenFlow14'))

        self.mininet_obj.start()

    def cleanup_mininet(self):

        if self.mininet_obj:
            print "Mininet cleanup..."
            #self.mininet_obj.stop()

        os.system("sudo mn -c")

    def get_all_switch_hosts(self, switch_id):

        p = self.topo.ports

        for node in p:

            # Only look for this switch's hosts
            if node != switch_id:
                continue

            for switch_port in p[node]:
                dst_list = p[node][switch_port]
                dst_node = dst_list[0]
                if dst_node.startswith("h"):
                    yield self.mininet_obj.get(dst_node)

    def _get_experiment_host_pair(self):

        for src_switch in self.topo.get_switches_with_hosts():
            for dst_switch in self.topo.get_switches_with_hosts():
                if src_switch == dst_switch:
                    continue

                # Assume one host per switch
                src_host = "h" + src_switch[1:] + "1"
                dst_host = "h" + dst_switch[1:] + "1"

                src_host_node = self.mininet_obj.get(src_host)
                dst_host_node = self.mininet_obj.get(dst_host)

                yield (src_host_node, dst_host_node)

    def is_host_pair_pingable(self, src_host, dst_host):
        hosts = [src_host, dst_host]
        ping_loss_rate = self.mininet_obj.ping(hosts, '1')

        # If some packets get through, then declare pingable
        if ping_loss_rate < 100.0:
            return True
        else:
            # If not, do a double check:
            cmd_output = src_host.cmd("ping -c 3 " + dst_host.IP())
            print cmd_output
            if cmd_output.find("0 received") != -1:
                return False
            else:
                return True

    def are_all_hosts_pingable(self):
        ping_loss_rate = self.mininet_obj.pingAll('1')

        # If some packets get through, then declare pingable
        if ping_loss_rate < 100.0:
            return True
        else:
            return False

    def get_intf_status(self, ifname):

        # set some symbolic constants
        SIOCGIFFLAGS = 0x8913
        null256 = '\0'*256

        # create a socket so we have a handle to query
        s = socket(AF_INET, SOCK_DGRAM)

        # call ioctl() to get the flags for the given interface
        result = fcntl.ioctl(s.fileno(), SIOCGIFFLAGS, ifname + null256)

        # extract the interface's flags from the return value
        flags, = struct.unpack('H', result[16:18])

        # check "UP" bit and print a message
        up = flags & 1

        return ('down', 'up')[up]

    def wait_until_link_status(self, sw_i, sw_j, intended_status):

        num_seconds = 0

        for link in self.mininet_obj.links:
            if (sw_i in link.intf1.name and sw_j in link.intf2.name) or (sw_i in link.intf2.name and sw_j in link.intf1.name):

                while True:
                    status_i = self.get_intf_status(link.intf1.name)
                    status_j = self.get_intf_status(link.intf2.name)

                    if status_i == intended_status and status_j == intended_status:
                        break

                    time.sleep(1)
                    num_seconds +=1

        return num_seconds

    def is_bi_connected_manual_ping_test(self, experiment_host_pairs_to_check, edges_to_try=None):

        is_bi_connected= True

        if not edges_to_try:
            edges_to_try = self.topo.g.edges()

        for edge in edges_to_try:

            # Only try and break switch-switch edges
            if edge[0].startswith("h") or edge[1].startswith("h"):
                continue

            for (src_host, dst_host) in experiment_host_pairs_to_check:

                is_pingable_before_failure = self.is_host_pair_pingable(src_host, dst_host)

                if not is_pingable_before_failure:
                    print "src_host:", src_host, "dst_host:", dst_host, "are not connected."
                    is_bi_connected = False
                    break

                self.mininet_obj.configLinkStatus(edge[0], edge[1], 'down')
                self.wait_until_link_status(edge[0], edge[1], 'down')
                time.sleep(5)
                is_pingable_after_failure = self.is_host_pair_pingable(src_host, dst_host)
                self.mininet_obj.configLinkStatus(edge[0], edge[1], 'up')
                self.wait_until_link_status(edge[0], edge[1], 'up')

                time.sleep(5)
                is_pingable_after_restoration = self.is_host_pair_pingable(src_host, dst_host)

                if not is_pingable_after_failure == True:
                    is_bi_connected = False
                    print "Got a problem with edge:", edge, " for src_host:", src_host, "dst_host:", dst_host
                    break

        return is_bi_connected

    def is_bi_connected_manual_ping_test_all_hosts(self,  edges_to_try=None):

        is_bi_connected= True

        if not edges_to_try:
            edges_to_try = self.topo.g.edges()

        for edge in edges_to_try:

            # Only try and break switch-switch edges
            if edge[0].startswith("h") or edge[1].startswith("h"):
                continue

            is_pingable_before_failure = self.are_all_hosts_pingable()

            if not is_pingable_before_failure:
                is_bi_connected = False
                break

            self.mininet_obj.configLinkStatus(edge[0], edge[1], 'down')
            self.wait_until_link_status(edge[0], edge[1], 'down')
            time.sleep(5)
            is_pingable_after_failure = self.are_all_hosts_pingable()
            self.mininet_obj.configLinkStatus(edge[0], edge[1], 'up')
            self.wait_until_link_status(edge[0], edge[1], 'up')

            time.sleep(5)
            is_pingable_after_restoration = self.are_all_hosts_pingable()

            if not is_pingable_after_failure == True:
                is_bi_connected = False
                break

        return is_bi_connected

    # mhasan: calibrate delay based on network toplogy
    # mhasan: lower index -> lower delay budget -> higher priority

    def calibrate_delay(self, base_delay_budget):

        #self.min_delay_budget_for_all_flows = base_delay_budget  # save for schedulability calculation

        diameter = nx.diameter(self.ng.get_node_graph())
        self.network_diameter = diameter  # save for schedulability calculation

        base_delay_budget *= diameter  # vary with topology as Rakesh K. mentioned



        delta = base_delay_budget/10  # a fraction that increase the delay requirement from flow to flow
        #delta = base_delay_budget / 5  # a fraction that increase the delay requirement from flow to flow
        #delta = 5 * base_delay_budget  # a fraction that increase the delay requirement from flow to flow

        for flow_id, current_flow in enumerate(self.flow_specs):
            # do for every odd (forward flow), reverse flow will be the same.
            if flow_id % 2 == 0:
                current_flow.delay_budget = base_delay_budget
                self.flow_specs[flow_id+1].delay_budget = base_delay_budget  # for reverse flow
                base_delay_budget += delta

