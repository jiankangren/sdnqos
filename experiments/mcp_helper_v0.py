__author__ = 'Monowar Hasan'

import networkx as nx
import sys
from collections import defaultdict
import math
import pandas as pd


class MCP_Helper(object):

    def __init__(self, nw_config, x=10):
        self.nw_config = nw_config
        self.x = x
        self.d = defaultdict(dict)
        self.pi = defaultdict(dict)

    def random_print(self):
        print "## printing nw graph"

        print 'mhasan print'

        #print self.ng.host_ids
        print self.nw_config.ng.host_ids
        print self.nw_config.ng.switch_ids

        mygp = self.nw_config.ng.get_node_graph()

        print 'print nodes'
        print mygp.nodes()

        print 'adjacency matrix'
        nx.write_adjlist(mygp, sys.stdout)  # write adjacency list to screen
        print 'end adjacency matrix'

        print "print nodes.."

        print(list(mygp.nodes()))

        print "print edges..."
        print(list(mygp.edges()))

        print "switch link data..."
        tt = list(self.nw_config.ng.get_all_link_data())

        for t in tt:
            print t.link_ports_dict
            print t.link_delay
            print t.link_bw

        print "print links (v2)..."

        tt = self.nw_config.ng.graph.edges()
        print tt[0][0]
        print tt[0][1]



        print "printing flow spec (v1)..."
        print self.nw_config.flow_specs[0].src_host_id
        print self.nw_config.flow_specs[0].dst_host_id

        print "Printing local variables..."
        print self.d

    # returns the link delay between node_1 and node_2 for a given flow
    def get_delay_constraint(self, node_1, node_2):
        ld = self.nw_config.ng.get_link_data(node_2, node_1)
        return ld.link_delay

    def get_delay_constraint_heuristic(self, node_1, node_2, delay_budget):
        dc = self.get_delay_constraint(node_1, node_2)
        return math.ceil((dc * self.x) / delay_budget) # Therorem 1 + Section 2.3 in Klara's Paper

    def get_bw_constraint(self, current_flow, node_1, node_2):
        ld = self.nw_config.ng.get_link_data(node_2, node_1)
        return float(current_flow.configured_rate_bps) / float(ld.link_bw) # Smruti's equation (type cast for div)

    def get_bw_constraint_heuristic(self, current_flow, node_1, node_2, hmax):
        bwc = self.get_bw_constraint(current_flow, node_1, node_2)
        return math.ceil((bwc * self.x) / hmax) # Therorem 1 in Klara's Paper

    def init_mcp(self, nw_graph, src):
        # print 'print nodes'
        # print nw_graph.nodes()

        for v in nw_graph.nodes():
            for i in range(self.x + 1):
                # self.d[v][i] = float("inf")
                self.d[v][i] = 100000000000 # a very big number
                #self.d[v][i] = 0
                self.pi[v][i] = float("nan")

        for i in range(self.x + 1):
            self.d[src][i] = 0

        # self.d["h1s1"][5] = 100

    def relax_mcp(self, u, v, k, current_flow, hmax, delay_budget, itr):
        if itr == 1:
            # w1 = self.get_delay_constraint(u, v)
            # w2 = self.get_bw_constraint_heuristic(current_flow, u, v, hmax)
            w1 = self.get_bw_constraint(current_flow, u, v)
            w2 = self.get_delay_constraint_heuristic(u, v, delay_budget)
            '''
        elif itr == 2:
            w1 = self.get_delay_constraint_heuristic(u, v, delay_budget)
            w2 = self.get_bw_constraint(current_flow, u, v)
            '''
        else:
            print "MCP pass should be 1 or 2!"
            raise NotImplementedError

        kprime = int(k + w2)
        # print "kprime is {}".format(kprime)
        # print "u, v is ({}, {})".format(u,v)

        if kprime <= self.x:
            # print "kprime:{}, w1: {}, w2: {}, d[v][k'] = {}, d[u][k]+w1 = {}".format(kprime, w1, w2, self.d[v][kprime],self.d[u][k] + w1)
            if self.d[v][kprime] > self.d[u][k] + w1:
                print "in if"
                self.d[v][kprime] = self.d[u][k] + w1
                self.pi[v][kprime] = u
                # print "== kprime {}, in path {} -> pred {}==".format(kprime, v, u)
                print "== kprime {},  {} ->  {}==".format(kprime, v, u)
                # print "==v,k is {},{} -> d[v][k]={}==".format(v, kprime, self.d[v][kprime])

        # print "this line"



    def print_dic(self, d_name):
        for keys, values in d_name.items():
            print(keys)
            print(values)



    def get_max_hop(self, nw_graph, src, dst):
        # print "== Calculating MST =="
        #nw_graph = self.nw_config.ng.get_node_graph()
        # calculate the MST
        mst = nx.minimum_spanning_tree(nw_graph)

        #pred, dist = nx.bellman_ford(mst, src, -1) # use weight -1 to get the longest hop

        # print sorted(dist.items())

        return nx.shortest_path_length(mst, source=src, target=dst, weight=-1)  # use weight -1 to get the longest hop

        #return len(sorted(pred.items()))


    def ebf_mcp(self, nw_graph, current_flow, itr):
        # calculate path using EBF algorithm
        hmax = self.get_max_hop(nw_graph, current_flow.src_host_id, current_flow.dst_host_id)

        self.init_mcp(nw_graph, current_flow.src_host_id)

        print "inside ebf_mcp routine"

        number_of_nodes = len(list(nw_graph.nodes()))

        # print nw_graph.nodes()
        # print "Number of nodes {}".format(number_of_nodes)
        for i in range(1, number_of_nodes):
            for k in range(self.x+1):
                for edge in nw_graph.edges():
                #for edge in self.nw_config.ng.graph.edges():
                    u = edge[0]
                    v = edge[1]
                    self.relax_mcp(u, v, k, current_flow, hmax, current_flow.delay_budget, itr)


    def check_solution(self, current_flow):
        for i in range(self.x+1):
            if self.d[current_flow.dst_host_id][i] <= current_flow.delay_budget:
                print "soution found at x={}".format(i)

    def extract_path(self, nw_graph, current_flow, k):

        path = []
        traverse_done = False
        current_node = current_flow.dst_host_id

        src_switch = current_flow.src_host_id[current_flow.src_host_id.find('s'):]
        print "src sw is {}".format(src_switch)

        print "Src: {}, Dst:{}".format(current_flow.src_host_id, current_flow.dst_host_id)
        # print "print s2: {}".format(self.pi["s2"][k])


        while not traverse_done:
            #if not math.isnan(self.pi[current_node][k]):
            if not pd.isnull(self.pi[current_node][k]):
                #print "current node is before {}".format(current_node)
                path.append(current_node)
                current_node = self.pi[current_node][k]
                #print "current node is new {}".format(current_node)
                # if nw_graph.node[current_node]["node_type"] == "switch":
                #     print "node {} is a switch".format(current_node)
                # if current_node == src_switch:
                #     path.append(current_flow.src_host_id)
                #     traverse_done = True
                if current_node == current_flow.src_host_id:
                    traverse_done = True
            elif current_node == src_switch:
                path.append(src_switch)
                path.append(current_flow.src_host_id)
                traverse_done = True
            else:
                print "null node"
                break

        # reverse to show from Src to Dst
        # return path.reverse()
        return path




    def calculate_path_by_mcp(self):
        print "### MCP routine is running ###"
        # self.x = 20
        nw_graph = self.nw_config.ng.get_node_graph()

        '''
        nw_graph = nx.Graph()
        nw_graph.add_node("s1")
        nw_graph.add_node("s2")
        nw_graph.add_node("s3")
        nw_graph.add_node("h1s1")
        nw_graph.add_node("h2s1")
        nw_graph.add_node("h1s2")
        nw_graph.add_node("h2s2")
        nw_graph.add_node("h1s3")
        nw_graph.add_node("h2s3")

        nw_graph.add_edge("s1", "s2")
        nw_graph.add_edge("s2", "s3")
        nw_graph.add_edge("s1", "h1s1")
        nw_graph.add_edge("s1", "h2s1")
        nw_graph.add_edge("s2", "h1s2")
        nw_graph.add_edge("s2", "h2s2")
        nw_graph.add_edge("s3", "h1s3")
        nw_graph.add_edge("s3", "h2s3")
        '''


        # TO DO : automate for all flows
        current_flow = self.nw_config.flow_specs[0]

        self.init_mcp(nw_graph, current_flow.src_host_id)
        #print self.d
        #self.print_dic(self.d)
        #self.print_dic(self.pi)
        # self.random_print()





        #print hmax


        tt = self.nw_config.ng.graph.edges()
        print self.get_delay_constraint(tt[0][0], tt[0][1])


        hmax = self.get_max_hop(nw_graph, current_flow.src_host_id, current_flow.dst_host_id)
        print "h_max is {}".format(hmax)

        # print "BW constraint heuristic (w2 prime) is {}".format(self.get_bw_constraint_heuristic(current_flow, tt[0][0], tt[0][1], hmax))
        # print "Delay constraint is {}".format(self.get_delay_constraint_heuristic(tt[0][0], tt[0][1], current_flow.delay_budget))
        # print "BW constraint (w2) is {}".format(self.get_bw_constraint(current_flow, tt[0][0], tt[0][1]))

        ld = self.nw_config.ng.get_link_data(tt[0][0], tt[0][1])
        # print "BW constraint basic is {}".format(ld.link_bw)


        print "BW req. of the flow: {}".format(current_flow.configured_rate_bps)
        #print "Delay basic is {}".format(self.get_delay_constraint(tt[0][0], tt[0][1]))

        print "== printing vertex=="
        print nw_graph.nodes()

        print "===priting edges==="

        for edge in nw_graph.edges():
            # for edge in self.nw_config.ng.graph.edges():
            u = edge[0]
            v = edge[1]
            print "u, v is ({},{})".format(u, v)
            '''
            print "Delay constraint (w1):{}".format(self.get_delay_constraint(u, v))
            print "Delay constraint heuristic (w1 prime):{}".format(
                self.get_delay_constraint_heuristic(u, v, current_flow.delay_budget))

            print "BW constraint (w2) is {}".format(self.get_bw_constraint(current_flow, u, v))
            print "BW constraint heuristic (w2 prime) is {}".format(
                self.get_bw_constraint_heuristic(current_flow, u,v, hmax))
            # print "Delay constraint is {}".format(self.get_delay_constraint_heuristic(tt[0][0], tt[0][1], current_flow.delay_budget))
            '''

            print "BW constraint (w1) is {}".format(self.get_bw_constraint(current_flow, u, v))
            print "Delay constraint heuristic (w2 prime):{}".format(
                self.get_delay_constraint_heuristic(u, v, current_flow.delay_budget))

        print "===priting src dst ==="
        print "src:{}, dst:{}".format(current_flow.src_host_id, current_flow.dst_host_id)


        # self.relax_mcp(tt[0][0], tt[0][1], 10, current_flow, hmax, current_flow.delay_budget, 1)
        # print self.pi

        self.ebf_mcp(nw_graph, current_flow, 1)


        # print self.pi
        print "==== checking solution ==="
        self.check_solution(current_flow)


        print "==== printing path ==="
        path  = self.extract_path(nw_graph, current_flow, self.x)
        path2 = path[::-1]

        # print "==== printing path ==="
        print path
        print path2