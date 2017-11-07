#__author__ = 'Monowar Hasan'
# from __future__ import division
import networkx as nx
import sys
from collections import defaultdict
import math
import pandas as pd
import random



class MCP_Helper(object):

    def __init__(self, nw_graph, hmax, delay_budget, bw_budget, bw_req_flow, x=10):
        self.nw_graph = nw_graph
        self.x = x
        self.d = defaultdict(dict)
        self.pi = defaultdict(dict)

        # this are for testing purposes only
        #self.hmax = 3 # TO DO: need to calculate from the graph
        self.hmax = hmax

        #self.bw_req_flow = 50 # MBPS
        self.bw_req_flow = bw_req_flow

        #self.link_bw = 100 # MBPS

        #self.bw_utilization = float(self.bw_req_flow) / float(self.link_bw)
        #self.link_delay = 3 # ms

        #self.delay_budget = 100 # ms
        self.delay_budget = delay_budget
        self.bw_budget = bw_budget

        #print "BW utilization {}".format(self.bw_utilization)

    def init_mcp(self, src, itr):
        # print 'print nodes'
        # print nw_graph.nodes()
        if itr == 1:
            loop_range = self.x
        elif itr == 2:
            loop_range = int(math.ceil(self.bw_budget))
        else:
            raise NotImplementedError

        for v in self.nw_graph.nodes():
            #for i in range(self.x + 1):
            for i in range(loop_range + 1):
                self.d[v][i] = float("inf")
                # self.d[v][i] = 100000000000 # a very big number
                # self.d[v][i] = 0
                self.pi[v][i] = float("nan")

        for i in range(self.x + 1):
            self.d[src][i] = 0.0

        # print self.d

    def get_bandwidth(self, u, v):

        '''

        if (u=="s" and v=="u") or (v=="s" and u=="u"):
            return 1.0
        elif (u=="s" and v=="v") or (v=="s" and u=="v"):
            return 1.0
        elif (u == "u" and v == "t") or (v == "u" and u == "t"):
            return 2.5
        elif (u == "u" and v == "v") or (v == "u" and u == "v"):
            return 1.0
        elif (u == "v" and v == "t") or (v == "v" and u == "t"):
            return 4.0
        else:
            raise NotImplementedError
        '''

        # return self.bw_utilization
        # return 0.5
        # return random.random()
        return float(self.bw_req_flow) / float(self.nw_graph[u][v]['link_bw'])

    def get_new_bandwidth(self, u, v):

        # bw_util = float(self.bw_req_flow) / float(self.nw_graph[u][v]['link_bw'])
        #C = self.hmax * self.bw_utilization
        # C = self.hmax * bw_util
        # return math.ceil((self.get_bandwidth(u, v) * self.x) / C)
        return math.ceil((self.get_bandwidth(u, v) * self.x) / self.bw_budget)

    def get_delay(self, u, v):

        # return 3.0 / 100.0
        # return self.link_delay/float(self.delay_budget)

        # return self.link_delay

        return self.nw_graph[u][v]['link_delay']

    def get_new_delay(self, u, v):

        '''
        if (u=="s" and v=="u") or (v=="s" and u=="u"):
            return 6.0
        elif (u=="s" and v=="v") or (v=="s" and u=="v"):
            return 10.0
        elif (u == "u" and v == "t") or (v == "u" and u == "t"):
            return 5.0
        elif (u == "u" and v == "v") or (v == "u" and u == "v"):
            return 3.0
        elif (u == "v" and v == "t") or (v == "v" and u == "t"):
            return 1.0
        else:
            raise NotImplementedError

        '''

        return math.ceil((self.get_delay(u, v) * self.x) / float(self.delay_budget))

        # return 3.0
        # return random.random()

    def relax_mcp(self, u, v, k, itr):

        if itr == 1:
            w1 = self.get_delay(u,v)
            w2_prime = self.get_new_bandwidth(u,v)
            loop_range = self.x

            # w1 = self.get_bandwidth(u, v)
            # w2_prime = self.get_new_delay(u, v)
            #print "(delay) = {}, (new-bw) = {}".format(w1, w2_prime)
        elif itr == 2:
            w1 = self.get_new_delay(u, v)
            w2_prime = self.get_bandwidth(u, v)
            loop_range = int(math.ceil(self.bw_budget))
            # print "(new-delay) = {}, (bw) = {}".format(w1, w2_prime)

            # smruti
            #w1 = self.get_bandwidth(u, v)
            #w2_prime = self.get_new_delay(u, v)
            #print "w1 (bw) = {}, w2prime (nw-delay) = {}".format(w1, w2_prime)

            # w1 = self.get_new_bandwidth(u, v)
            # w2_prime = self.get_delay(u, v)

        else:
            raise NotImplementedError



        kprime = int(k + w2_prime)  # print "kprime is {}".format(kprime)
        # print "u, v is ({}, {})".format(u, v)
        # print "kprime:{}, w1({},{})={}, w2_prime({},{})={}".format(kprime, u, v, w1, u, v, w2_prime)
        # print "d[{}][{}] = {}, d[{}][{}] + w1 = {}".format(v,kprime, self.d[v][kprime], u, k, self.d[u][k] + w1)

        #if kprime <= self.x:
        if kprime <= loop_range:
            #print "kprime is {}".format(kprime)
            # print "(v, u):({},{}) - {} -> {}".format(v, u, self.d[v][kprime], self.d[u][k] + w1)
            if self.d[v][kprime] > self.d[u][k] + w1:
                #print "in if"
                self.d[v][kprime] = self.d[u][k] + w1
                self.pi[v][kprime] = u
                # print "== kprime {}, {} -> {}  ==".format(kprime, v, u)

                # print "this line"

    def calculate_mcp_ebf(self, src, dst, itr):
        print "== Calculating MCP_EBF==="

        if itr == 1:
            loop_range = self.x
        elif itr == 2:
            loop_range = int(math.ceil(self.bw_budget))
        else:
            raise NotImplementedError


        self.init_mcp(src, itr)

        number_of_nodes = len(list(self.nw_graph.nodes()))
        for i in range(1, number_of_nodes):
        # for i in range(number_of_nodes):
            # for k in range(self.x+1):
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
            loop_range = int(math.ceil(self.bw_budget))
        else:
            raise NotImplementedError

        while not traverse_done:
            #for k in range(self.x + 1):
            for k in range(loop_range + 1):
                if not pd.isnull(self.pi[current_node][k]):
                    path.append(current_node)
                    current_node = self.pi[current_node][k]
                    break
                if current_node == src:
                    path.append(current_node)
                    traverse_done = True
                    break
            '''
            else:
                print "null node"
                break
            '''

        # reverse to show from Src to Dst
        # return path.reverse()
        return path

    def check_solution(self, dst, itr):
        if itr == 1:
            c1 = self.delay_budget
        elif itr==2:
            c1 = self.x
        else:
            raise NotImplementedError

        for k in range(self.x+1):
            if self.d[dst][k] <= c1:
                return True

        return False

    def get_path_layout(self, src, dst):
        path_src_2_dst =  []
        itr = 2
        for i in range(1, itr + 1):
            # print "iteration {}".format(i)

            self.calculate_mcp_ebf(src, dst, i)

            if self.check_solution(dst, i):
                print "Path found at pass {}".format(i)
                path = self.extract_path(src, dst, i)
                path_src_2_dst = path[::-1]
                # print path_src_2_dst
                # break
                return path_src_2_dst
            else:
                print "Unable to find path at pass {}".format(i)

        return path_src_2_dst

def print_graph(nw_graph):

    print "print nodes.."
    #print(list(nw_graph.nodes()))
    print nw_graph.nodes()

    print "print edges..."
    # print(list(nw_graph.edges()))
    print nw_graph.edges()

    '''
    print 'adjacency matrix'
    nx.write_adjlist(nw_graph, sys.stdout)  # write adjacency list to screen
    print 'end adjacency matrix'
    '''


def get_bw_budget(nw_graph, bw_req_flow, hmax):
    max_bw_util = 0
    for i in nw_graph.edges():
        bw_util = hmax * float(bw_req_flow) / float(nw_graph[i[0]][i[1]]['link_bw'])
        if bw_util >= max_bw_util:
            max_bw_util = bw_util

    return max_bw_util

def calibrate_graph(graph):
    nw_graph = nx.DiGraph()

    for i in graph.nodes():
        nw_graph.add_node(i)

    # create bidirectional links
    for i in graph.edges():
        link_delay = graph[i[0]][i[1]]['link_delay']
        link_bw = graph[i[0]][i[1]]['link_bw']
        nw_graph.add_edge(i[0], i[1], link_delay=link_delay, link_bw=link_bw)
        nw_graph.add_edge(i[1], i[0], link_delay=link_delay, link_bw=link_bw)

    return nw_graph


def calculate_hmax(nw_graph):
    #mst = nx.minimum_spanning_tree(nw_graph)

    # use weight -1 to get the longest hop
    #hmax = nx.shortest_path_length(mst, source=src, target=dst, weight=-1)  # use weight -1 to get the longest hop
    #hmax = nx.shortest_path_length(nw_graph, source=src, target=dst, weight=-1)  # use weight -1 to get the longest hop

    #print_graph(mst)
    hmax = nx.number_of_nodes(nw_graph)

    print "hmax  is {}".format(hmax)
    return hmax

def main():
    print "this is main"

    """
    mygraph = nx.Graph()
    mygraph.add_node("s")
    mygraph.add_node("u")
    mygraph.add_node("v")
    mygraph.add_node("t")

    mygraph.add_edge("s", "u")
    mygraph.add_edge("s", "v")
    mygraph.add_edge("u", "v")
    mygraph.add_edge("u", "t")
    mygraph.add_edge("v", "t")

    print "=== my original graph ==="
    print_graph(mygraph)

    newmygraph = calibrate_graph(mygraph)
    print "=== my new graph ==="
    print_graph(newmygraph)
    print "== done =="
    """


    #nw_graph = nx.Graph()
    nw_graph = nx.DiGraph()



    '''

    nw_graph.add_node("s")
    nw_graph.add_node("u")
    nw_graph.add_node("v")
    nw_graph.add_node("t")
    #nw_graph.add_node("z")



    nw_graph.add_edge("s", "u")
    nw_graph.add_edge("s", "v")
    nw_graph.add_edge("u", "v")
    nw_graph.add_edge("u", "t")
    #nw_graph.add_edge("u", "z")
    nw_graph.add_edge("v", "t")
    #nw_graph.add_edge("v", "z")

    nw_graph.add_edge("u", "s")
    nw_graph.add_edge("v", "s")
    nw_graph.add_edge("v", "u")
    nw_graph.add_edge("t", "u")
    nw_graph.add_edge("t", "v")
    '''



    link_delay = 3 # ms
    link_bw = 100  # MBPS
    delay_budget = 100  # ms
    bw_req_flow = 50  # MBPS

    #'''
    src = "h1s2"
    dst = "h1s1"


    #nw_graph = nx.DiGraph()
    nw_graph = nx.Graph()
    nw_graph.add_node("s1")
    nw_graph.add_node("s2")
    nw_graph.add_node("h1s1")
    nw_graph.add_node("h1s2")
    nw_graph.add_node("h2s2")
    nw_graph.add_node("h2s1")

    nw_graph.add_edge("s2", "h2s2", link_delay=link_delay, link_bw=link_bw)
    #print "Link delay="
    #print nw_graph["s2"]["h2s2"]['link_delay']

    nw_graph.add_edge("s2", "s1", link_delay=link_delay, link_bw=link_bw)
    nw_graph.add_edge("s2", "h1s2", link_delay=link_delay, link_bw=link_bw)
    nw_graph.add_edge("s1", "h2s1", link_delay=link_delay, link_bw=link_bw)
    nw_graph.add_edge("s1", "h1s1", link_delay=link_delay, link_bw=link_bw)


    #'''

    '''
    nw_graph = nx.Graph()

    nw_graph.add_node("s")
    nw_graph.add_node("u")
    nw_graph.add_node("v")
    nw_graph.add_node("t")

    nw_graph.add_edge("s", "u", link_delay=link_delay, link_bw=link_bw)
    nw_graph.add_edge("s", "v", link_delay=link_delay, link_bw=link_bw)
    nw_graph.add_edge("u", "v", link_delay=link_delay, link_bw=link_bw)
    nw_graph.add_edge("u", "t", link_delay=link_delay, link_bw=link_bw)
    nw_graph.add_edge("v", "t", link_delay=link_delay, link_bw=link_bw)

    src = "s"
    dst = "t"
    '''
    x = 10

    hmax = calculate_hmax(nw_graph)
    #hmax = 3
    bw_budget = get_bw_budget(nw_graph, bw_req_flow, hmax)
    print "BW budget = {}".format(bw_budget)
    # hmax = 3

    print_graph(nw_graph)

    print "=== after calibration === "
    nw_graph = calibrate_graph(nw_graph)
    print_graph(nw_graph)

    # print "w1(u,v): {}, w2_prime(u,v): {}".format(get_w1(0,0), get_w2_prime(0,0))


    # mh = MCP_Helper(nw_graph, delay_budget, bw_req_flow, x)
    #mh.calculate_mcp_ebf("s", "t")

    mh = MCP_Helper(nw_graph, hmax, delay_budget, bw_budget, bw_req_flow, x)


    '''
    itr = 2
    for i in range(1, itr+1):
        print "iteration {}".format(i)

        mh.calculate_mcp_ebf(src, dst, i)

        if mh.check_solution(dst, i):
            print "Path found at iteration {}".format(i)
            path = mh.extract_path(src, dst)
            path_src_2_dst = path[::-1]
            print path_src_2_dst
            break
        else:
            print "Unable to find path at pass {}".format(i)

    '''

    path = mh.get_path_layout(src, dst)
    if  not path:
        print "No path found!"
    else:
        print path

    #path = mh.extract_path("s", "t")






if __name__ == "__main__":
    main()