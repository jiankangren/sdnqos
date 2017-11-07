__author__ = 'Monowar Hasan'
# from __future__ import division
import networkx as nx
# import sys
from collections import defaultdict
import math
import pandas as pd
# import random
from model.intent import Intent
from synthesis.synthesis_lib import SynthesisLib

from copy import deepcopy


class MCPHelper(object):

    def __init__(self, nw_graph, hmax, delay_budget, bw_budget, bw_req_flow, x=10):
        self.nw_graph = nw_graph
        self.x = x
        self.d = defaultdict(dict)
        self.pi = defaultdict(dict)

        self.hmax = hmax
        self.bw_req_flow = bw_req_flow
        self.delay_budget = delay_budget
        self.bw_budget = bw_budget

    def init_mcp(self, src, itr):

        if itr == 1:
            loop_range = self.x
        elif itr == 2:
            loop_range = int(math.floor(self.bw_budget))
        else:
            raise NotImplementedError

        for v in self.nw_graph.nodes():
            for i in range(loop_range + 1):
                self.d[v][i] = float("inf")
                self.pi[v][i] = float("nan")

        for i in range(self.x + 1):
            self.d[src][i] = 0.0

    def get_bandwidth(self, u, v):

        return float(self.bw_req_flow) / float(self.nw_graph[u][v]['link_bw'])

    def get_new_bandwidth(self, u, v):

        return math.ceil((self.get_bandwidth(u, v) * self.x) / self.bw_budget)

    def get_delay(self, u, v):

        return self.nw_graph[u][v]['link_delay']

    def get_new_delay(self, u, v):

        return math.ceil((self.get_delay(u, v) * self.x) / float(self.delay_budget))

    def relax_mcp(self, u, v, k, itr):

        if itr == 1:
            w1 = self.get_delay(u,v)
            w2_prime = self.get_new_bandwidth(u,v)
            loop_range = self.x

        elif itr == 2:
            w1 = self.get_new_delay(u, v)
            w2_prime = self.get_bandwidth(u, v)
            loop_range = int(math.floor(self.bw_budget))

        else:
            raise NotImplementedError

        kprime = int(k + w2_prime)

        if kprime <= loop_range:
            if self.d[v][kprime] > self.d[u][k] + w1:
                self.d[v][kprime] = self.d[u][k] + w1
                self.pi[v][kprime] = u

    def calculate_mcp_ebf(self, src, dst, itr):

        # print "=== Calculating MCP_EBF ==="

        if itr == 1:
            loop_range = self.x
        elif itr == 2:
            loop_range = int(math.floor(self.bw_budget))
        else:
            raise NotImplementedError

        self.init_mcp(src, itr)

        number_of_nodes = len(list(self.nw_graph.nodes()))
        for i in range(1, number_of_nodes):
            for k in range(loop_range+1):
                for edge in self.nw_graph.edges():
                    u = edge[0]
                    v = edge[1]
                    self.relax_mcp(u, v, k, itr)

    def extract_path(self, src, dst, itr):

        path = []
        traverse_done = False
        current_node = dst

        if itr == 1:
            loop_range = self.x
        elif itr == 2:
            loop_range = int(math.floor(self.bw_budget))
        else:
            raise NotImplementedError

        count = 0
        maxcount = 1000000  # some arbitrary large number
        while not traverse_done:
            count += 1
            if count > maxcount:
                raise ValueError('Unable to find path within maximum timeout')

            for k in range(loop_range + 1):
                if not pd.isnull(self.pi[current_node][k]):
                    path.append(current_node)
                    current_node = self.pi[current_node][k]
                    break
                if current_node == src:
                    path.append(current_node)
                    traverse_done = True
                    break

        return path

    def check_solution(self, dst, itr):
        if itr == 1:
            c1 = self.delay_budget
        elif itr == 2:
            c1 = self.x
        else:
            raise NotImplementedError

        for k in range(self.x+1):
            if self.d[dst][k] <= c1:
                return True

        return False

    def get_path_layout(self, src, dst):
        path_src_2_dst = []
        itr = 2
        for i in range(1, itr + 1):

            self.calculate_mcp_ebf(src, dst, i)

            if self.check_solution(dst, i):
                print "Path found at pass {}".format(i)
                path = self.extract_path(src, dst, i)
                path_src_2_dst = path[::-1]
                return path_src_2_dst
            else:
                print "Unable to find path at pass {}".format(i)

        return path_src_2_dst


def print_graph(nw_graph):

    print "print nodes.."
    print nw_graph.nodes()

    print "print edges..."
    print nw_graph.edges()

    '''
    print 'adjacency matrix'
    nx.write_adjlist(nw_graph, sys.stdout)  # write adjacency list to screen
    print 'end adjacency matrix'
    '''


def get_bw_budget(nw_config, bw_req_flow, hmax):
    max_bw_util = 0
    nw_graph = nw_config.ng.get_node_graph()
    for i in nw_graph.edges():
        ld = nw_config.ng.get_link_data(i[0], i[1])
        link_bw = ld.link_bw
        bw_util = hmax * float(bw_req_flow) / float(link_bw)
        # bw_util = hmax * float(bw_req_flow) / float(nw_graph[i[0]][i[1]]['link_bw'])
        if bw_util >= max_bw_util:
            max_bw_util = bw_util

    return max_bw_util


def calibrate_graph(nw_config):

    nw_graph = nx.DiGraph()
    graph = nw_config.ng.get_node_graph()

    for i in graph.nodes():
        nw_graph.add_node(i)

    # create bidirectional links
    for i in graph.edges():
        ld = nw_config.ng.get_link_data(i[0], i[1])
        link_delay = ld.link_delay
        link_bw = ld.link_bw
        nw_graph.add_edge(i[0], i[1], link_delay=link_delay, link_bw=link_bw)
        nw_graph.add_edge(i[1], i[0], link_delay=link_delay, link_bw=link_bw)

    return nw_graph


def calculate_hmax(nw_graph):

    hmax = nx.number_of_nodes(nw_graph)
    return hmax


def update_reamining_bw(nw_graph, current_flow):
    # print "updating remaining bw..."
    # reduce the bw that allocated to that flow-path
    for i in range(1, len(current_flow.path) - 1):
        nw_graph[current_flow.path[i]][current_flow.path[i+1]]['link_bw'] -= current_flow.configured_rate_bps
        nw_graph[current_flow.path[i+1]][current_flow.path[i]]['link_bw'] -= current_flow.configured_rate_bps
        # print "link{}->{}, current bw:{}".format(current_flow.path[i], current_flow.path[i+1], nw_graph[current_flow.path[i]][current_flow.path[i+1]]['link_bw'])


def print_path(nw_config):

    print "....Printing flow path...."

    for current_flow in nw_config.flow_specs:
        path = current_flow.path
        if not path:
            print "No path found for flow {} to {}".format(current_flow.src_host_id, current_flow.dst_host_id)
        else:
            print "Path found for flow {} to {}".format(current_flow.src_host_id, current_flow.dst_host_id)
            print path


def print_delay_budget(nw_config):

    print "....Printing delay budget...."

    for current_flow in nw_config.flow_specs:
        print "Delay budget for flow {} to {} is {}".format(current_flow.src_host_id, current_flow.dst_host_id,
                                                            current_flow.delay_budget)



def find_path_by_mcp(nw_config, x=10):
    nw_graph = nw_config.ng.get_node_graph()

    for flow_id, current_flow in enumerate(nw_config.flow_specs):

        # do for every odd (forward flow), reverse flow will be the same.
        if flow_id % 2 == 0:

            src = current_flow.src_host_id
            dst = current_flow.dst_host_id

            if current_flow.tag == "real-time":
                bw_req_flow = current_flow.configured_rate_bps
                hmax = calculate_hmax(nw_graph)
                delay_budget = current_flow.delay_budget
                bw_budget = get_bw_budget(nw_config, bw_req_flow, hmax)
                nw_graph = calibrate_graph(nw_config)
                mh = MCPHelper(nw_graph, hmax, delay_budget, bw_budget, bw_req_flow, x)
                path = mh.get_path_layout(src, dst)

            elif current_flow.tag == "best-effort":
                #print "Finding best-effort path"
                path = nx.shortest_path(nw_config.ng.get_node_graph(),source=src,target=dst)
                #print pp

            else:
                raise NotImplementedError

            if not path:
                print "No path found for flow {} to {}".format(current_flow.src_host_id, current_flow.dst_host_id)
            else:
                print "Path found for {} flow {} to {}".format(current_flow.tag, current_flow.src_host_id, current_flow.dst_host_id)
                print path
                # set the path for the flow
                current_flow.path = path
                reverse_path = path[::-1] # path for the reverse flow
                nw_config.flow_specs[flow_id+1].path = reverse_path  # set the path for the reverse flow

                # decrease the available bw in the path
                update_reamining_bw(nw_graph, current_flow)


def test_all_flow_is_schedulable(nw_config):

    for current_flow in nw_config.flow_specs:
        if not current_flow.path:
            return False

    return True


# Intents uses individual queue
def compute_path_intents(network_graph, fs):

    intent_list = []

    # Get the port where the host connects at the first switch in the path
    link_ports_dict = network_graph.get_link_ports_dict(fs.ng_src_host.node_id, fs.ng_src_host.sw.node_id)
    in_port = link_ports_dict[fs.ng_src_host.sw.node_id]

    # This loop always starts at a switch
    for i in range(1, len(fs.path) - 1):

        link_ports_dict = network_graph.get_link_ports_dict(fs.path[i], fs.path[i+1])

        fwd_flow_match = deepcopy(fs.flow_match)
        mac_int = int(fs.ng_dst_host.mac_addr.replace(":", ""), 16)
        fwd_flow_match["ethernet_destination"] = int(mac_int)

        intent = Intent("primary",
                        fwd_flow_match,
                        in_port,
                        link_ports_dict[fs.path[i]],
                        True,
                        min_rate=fs.configured_rate_bps,
                        max_rate=fs.configured_rate_bps)

        # Store the switch id in the intent
        intent.switch_id = fs.path[i]

        intent_list.append(intent)
        in_port = link_ports_dict[fs.path[i+1]]

    return intent_list


# Intents uses default queue
def compute_path_intents_defualt_queue(network_graph, fs):

    intent_list = []

    # Get the port where the host connects at the first switch in the path
    link_ports_dict = network_graph.get_link_ports_dict(fs.ng_src_host.node_id, fs.ng_src_host.sw.node_id)
    in_port = link_ports_dict[fs.ng_src_host.sw.node_id]

    # This loop always starts at a switch
    for i in range(1, len(fs.path) - 1):

        link_ports_dict = network_graph.get_link_ports_dict(fs.path[i], fs.path[i+1])

        fwd_flow_match = deepcopy(fs.flow_match)
        mac_int = int(fs.ng_dst_host.mac_addr.replace(":", ""), 16)
        fwd_flow_match["ethernet_destination"] = int(mac_int)

        intent = Intent("primary",
                        fwd_flow_match,
                        in_port,
                        link_ports_dict[fs.path[i]],
                        True,
                        min_rate=None,
                        max_rate=None)

        # Store the switch id in the intent
        intent.switch_id = fs.path[i]

        intent_list.append(intent)
        in_port = link_ports_dict[fs.path[i+1]]

    return intent_list


def synthesize_flow_specifications(nc):

    synthesis_lib = SynthesisLib("localhost", "8181", nc.ng)

    print "Synthesizing rules and queues in the switches..."

    for fs in nc.flow_specs:

        # Compute intents for the path of the fs
        intent_list = compute_path_intents(nc.ng, fs)

        # Push intents one by one to the switches
        for intent in intent_list:
            synthesis_lib.push_destination_host_mac_intent_flow_with_qos(intent.switch_id, intent, 0, 100)


# goes to default queue, no rate-limiting and other features. good for best-effort flows
def synthesize_flow_specifications_default_queue(nc):

    synthesis_lib = SynthesisLib("localhost", "8181", nc.ng)

    print "Synthesizing (best-effort) rules in the switches..."

    for fs in nc.flow_specs:

        # Compute intents for the path of the fs
        intent_list = compute_path_intents_defualt_queue(nc.ng, fs)

        # Push intents one by one to the switches
        for intent in intent_list:
            synthesis_lib.push_destination_host_mac_intent_flow_default_queue(intent.switch_id, intent, 0, 100)


# synthesize each flow with proposed QoS guarantee
def synthesize_each_flow_qos(nc, fs, synthesis_lib):

    # Compute intents for the path of the fs
    intent_list = compute_path_intents(nc.ng, fs)

    # Push intents one by one to the switches
    for intent in intent_list:
        synthesis_lib.push_destination_host_mac_intent_flow_with_qos(intent.switch_id, intent, 0, 100)


# goes to default queue, no rate-limiting and other features. good for best-effort flows
def synthesize_each_flow_default_queue(nc, fs, synthesis_lib):

    # Compute intents for the path of the fs
    intent_list = compute_path_intents_defualt_queue(nc.ng, fs)

    # Push intents one by one to the switches
    for intent in intent_list:
        synthesis_lib.push_destination_host_mac_intent_flow_default_queue(intent.switch_id, intent, 0, 100)


## synthesize flow rules with best effort flow support

def synthesize_flow_specifications_with_best_effort(nc):

    synthesis_lib = SynthesisLib("localhost", "8181", nc.ng)

    print "Synthesizing rules and queues in the switches..."

    for fs in nc.flow_specs:

        if fs.tag == "real-time":
            print "Synthesizing Real-Time Flow!"
            synthesize_each_flow_qos(nc, fs, synthesis_lib)
        elif fs.tag == "best-effort":
            print "Synthesizing Best-Effort Flow!"
            synthesize_each_flow_default_queue(nc, fs, synthesis_lib)
        else:
            raise NotImplementedError

