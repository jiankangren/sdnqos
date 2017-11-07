__author__ = 'Monowar Hasan'

import sys
import os
import time
from collections import defaultdict
import socket

sys.path.append("./")
sys.path.append("../")

from controller_man import ControllerMan
from experiment import Experiment
from network_configuration import NetworkConfiguration
from flow_specification import FlowSpecification
from model.match import Match

# mhasan import
#from mcp_helper import MCP_Helper
import mcp_helper as mcph
import random
import itertools
import pickle
import networkx as nx
import numpy as np

import signal


class MyTimeOutException(Exception):
    pass


def timeout(signum, frame):
    raise MyTimeOutException("Timeout!")


class QosDemo(Experiment):

    def __init__(self,
                 num_iterations,
                 network_configurations,
                 num_measurements,
                 measurement_rates,
                 number_of_test_cases,
                 number_of_RT_flow_list,
                 number_of_BE_flow_list,
                 base_delay_budget,
                 link_delay_upper_bound):

        super(QosDemo, self).__init__("number_of_hosts", num_iterations)
        self.network_configurations = network_configurations
        self.num_measurements = num_measurements

        self.measurement_rates = measurement_rates

        self.number_of_test_cases = number_of_test_cases
        self.number_of_RT_flow_list = number_of_RT_flow_list
        self.number_of_BE_flow_list = number_of_BE_flow_list

        self.base_delay_budget = base_delay_budget
        self.link_delay_upper_bound = link_delay_upper_bound

        self.cm = ControllerMan(controller="ryu")
        self.cm.stop_controller()
        time.sleep(5)
        self.controller_port = self.cm.start_controller()

        self.data = {
            "Throughput": defaultdict(defaultdict),
            "99th Percentile Latency": defaultdict(defaultdict),
            "Maximum Latency": defaultdict(defaultdict)
        }

    def trigger(self):

        for nc in self.network_configurations:
            print "network_configuration:", nc

            nc.setup_network_graph(mininet_setup_gap=1, synthesis_setup_gap=1)
            nc.init_flow_specs()
            nc.calibrate_delay(self.base_delay_budget)

            # mhasan: MCP code will go there
            # mcph.print_delay_budget(nc)

            mcph.find_path_by_mcp(nc)  # update the path in 'path' variable of FlowSpecification

            if not mcph.test_all_flow_is_schedulable(nc):
                print "Network configuration is NOT feasible (no path found)!"
                nc.isFeasible = False
                continue

            # mcph.print_path(nc)
            # with only RT_flows
            # mcph.synthesize_flow_specifications(nc)

            # usues default queue (no delay-guarantee)
            #mcph.synthesize_flow_specifications_default_queue(nc)

            # Synthesize flows (may have both RT and BE
            mcph.synthesize_flow_specifications_with_best_effort(nc)

            # nc.mininet_obj.pingAll('1')
            self.measure_flow_rates(nc)

        self.parse_flow_measurement_output()
        print "Experiment Done!"

    def parse_iperf_output(self, iperf_output_string):
        data_lines =  iperf_output_string.split('\r\n')
        interesting_line_index = None
        for i in xrange(len(data_lines)):
             if data_lines[i].endswith('Server Report:'):
                interesting_line_index = i + 1
        data_tokens =  data_lines[interesting_line_index].split()
        print "Transferred Rate:", data_tokens[7]
        print "Jitter:", data_tokens[9]

    def parse_ping_output(self,ping_output_string):

        data_lines = ping_output_string.split('\r\n')
        interesting_line_index = None
        for i in xrange(len(data_lines)):
            if data_lines[i].startswith('5 packets transmitted'):
                interesting_line_index = i + 1
        data_tokens = data_lines[interesting_line_index].split()
        data_tokens = data_tokens[3].split('/')
        print 'Min Delay:', data_tokens[0]
        print 'Avg Delay:', data_tokens[1]
        print 'Max Delay:', data_tokens[2]

    def measure_flow_rates(self, nc):

        for i in range(self.num_iterations):
            print "iteration:", i + 1

            for j in range(self.num_measurements):

                max_fs_duration = 0
                os.system('killall netserver')  # kill all previous netserver instance

                for fs in nc.flow_specs:

                    if not fs.measurement_rates:
                        continue

                    server_command = "/usr/local/bin/netserver"
                    server_output = fs.mn_dst_host.cmd(server_command)
                    client_output = fs.mn_src_host.cmd(fs.construct_netperf_cmd_str(fs.measurement_rates[j]))

                    if fs.tests_duration > max_fs_duration:
                        max_fs_duration = fs.tests_duration

                # Sleep for 5 seconds more than flow duration to make sure netperf has finished.
                time.sleep(max_fs_duration + 5)

                fcnt = 0  # a counter to print flow number
                for fs in nc.flow_specs:

                    if not fs.measurement_rates:
                        continue

                    fcnt += 1

                    signal.signal(signal.SIGALRM, timeout)
                    # see whether there is any output from netperf
                    signal.alarm(10)

                    print "Running for flow-id: {}".format(fcnt)
                    try:
                        netperf_output_string = fs.mn_src_host.read()
                    except MyTimeOutException:
                        print "==== Timeout while reading netperf output. Aborting... ===="
                        continue
                    else:
                        # disable alarm
                        signal.alarm(0)
                        signal.signal(signal.SIGALRM, signal.SIG_DFL)

                        print "Delay Budget (e2e):{} microsecond, Max possible delay (round-trip):{} microsecond.".format(
                            fs.delay_budget*1000*1000,  # in us
                            # link_delay_upper bound in us
                            self.link_delay_upper_bound * nx.diameter(nc.ng.get_node_graph()) * 2)


                        print "=== netperf output: [Flow {} to {} ({}), Rate: {}, Test ID: {}, #of RT-Flow: {}, #of BE-Flow: {}, Flow ID: {}] ===".format(
                            fs.src_host_id, fs.dst_host_id, fs.tag,
                            fs.measurement_rates[j], nc.test_case_id, nc.number_of_RT_flows, nc.number_of_BE_flows,
                            fcnt)

                        print netperf_output_string

                        try:
                            s1 = fs.parse_measurements(netperf_output_string)
                        except StandardError:
                            print "Invalid result from netperf. Unable to parse Flow ID {}!".format(fcnt)
                            fs.measurements[fs.measurement_rates[j]].append(fs.get_null_measurement())
                        else:
                            fs.measurements[fs.measurement_rates[j]].append(fs.parse_measurements(netperf_output_string))
                            #print "saving netperf results!"

    def parse_flow_measurement_output(self):

        output_data_list = []  # maximum latency in any iteration for each of the flows

        for nc in self.network_configurations:

            # checking whether we have any solution for the network configuration
            if not nc.isFeasible:
                continue

            for j in range(self.num_measurements):

                max_mean_latency = 0
                max_max_latency = 0
                max_nn_latency = 0
                min_throughput = "inf"
                max_delay_budget = 0
                min_delay_budget = "inf"

                for fs in nc.flow_specs:
                    if not fs.measurement_rates:
                        continue

                    # we consider only real-time flows measurements
                    if fs.tag == "best-effort":
                        # print "best-effort, ignoring....."
                        continue

                    tmp = fs.measurements[fs.measurement_rates[j]]

                    mean_latency_list = [d['mean_latency'] for d in tmp if 'mean_latency' in d]
                    max_latency_list = [d['max_latency'] for d in tmp if 'max_latency' in d]
                    nn_latency_list = [d['nn_perc_latency'] for d in tmp if 'nn_perc_latency' in d]
                    min_throughput_list = [d['throughput'] for d in tmp if 'throughput' in d]

                    # take only +ve
                    mean_latency_list = [x for x in mean_latency_list if x >= 0]
                    max_latency_list = [x for x in max_latency_list if x >= 0]
                    nn_latency_list = [x for x in nn_latency_list if x >= 0]
                    min_throughput_list = [x for x in min_throughput_list if x >= 0]

                    # max_mean_latency_iter = max(mean_latency_list)
                    # max_max_latency_iter = max(max_latency_list)  # saves the max of maximum latency
                    # max_nn_latency_iter = max(nn_latency_list)  # 99P latency
                    # min_throughput_iter = min(min_throughput_list)  # saves minimum throughput

                    max_mean_latency_iter = np.mean(np.array(mean_latency_list).astype(np.float))
                    max_max_latency_iter = np.mean(np.array(max_latency_list).astype(np.float))  # saves the mean of maximum latency
                    max_nn_latency_iter = np.mean(np.array(nn_latency_list).astype(np.float))  # 99P latency
                    min_throughput_iter = np.mean(np.array(min_throughput_list).astype(np.float))  # saves minimum throughput

                    if max_mean_latency_iter > max_mean_latency:
                        max_mean_latency = max_mean_latency_iter

                    if max_max_latency_iter > max_max_latency:
                        max_max_latency = max_max_latency_iter

                    if max_nn_latency_iter > max_nn_latency:
                        max_nn_latency = max_nn_latency_iter

                    if min_throughput_iter < min_throughput:
                        min_throughput = min_throughput_iter

                    if fs.delay_budget > max_delay_budget:
                        max_delay_budget = fs.delay_budget

                    if fs.delay_budget < min_delay_budget:
                        min_delay_budget = fs.delay_budget

                diameter = nx.diameter(nc.ng.get_node_graph())
                max_possible_delay = self.link_delay_upper_bound * diameter
                max_possible_delay *= 1000  # convert to microsecond (since netperf output in microsecond)
                max_bw_req = max(self.measurement_rates)

                val_dict = {"number_of_RT_flows": nc.number_of_RT_flows,
                            "number_of_BE_flows": nc.number_of_BE_flows,
                            "max_possible_delay_e2e": max_possible_delay,  # this is end-to-end (NOT round-trip)
                            "measurement_rates": self.measurement_rates[j],
                            "max_mean_latency": float(max_mean_latency),
                            "max_max_latency": float(max_max_latency),
                            "max_nn_latency": float(max_nn_latency),
                            "min_throughput": float(min_throughput),
                            "max_delay_budget_e2e": max_delay_budget * 1000000,  # in microsecond
                            "min_delay_budget_e2e": min_delay_budget * 1000000,  # in microsecond
                            "max_bw_req": max_bw_req}

                output_data_list.append(val_dict)


        #print output_data_list
        # save data to workspace for plotting
        print "Writing data as pickle object..."
        with open('objs.pickle', 'w') as f:
            pickle.dump([self.number_of_RT_flow_list,
                         self.number_of_BE_flow_list,
                         self.number_of_test_cases,
                         self.measurement_rates,
                         self.base_delay_budget,
                         output_data_list], f)


def prepare_network_configurations(num_hosts_per_switch_list,
                                   same_output_queue_list, measurement_rates, tests_duration,
                                   topo_link_params, delay_budget,
                                   number_of_switches,
                                   number_of_RT_flow_list,
                                   number_of_BE_flow_list,
                                   test_case_list,
                                   cap_rate
                                   ):
    nc_list = []

    for test_case in range(test_case_list):

        for same_output_queue in same_output_queue_list:

            for hps in num_hosts_per_switch_list:

                for number_of_RT_flows in number_of_RT_flow_list:
                    for number_of_BE_flows in number_of_BE_flow_list:
                        flow_specs = prepare_flow_specifications(measurement_rates, tests_duration,
                                                                 number_of_switches,
                                                                 hps,
                                                                 number_of_RT_flows,
                                                                 number_of_BE_flows,
                                                                 delay_budget,
                                                                 cap_rate)

                        # mhasan: change with link params
                        nc = NetworkConfiguration("ryu",
                                                  "random_with_param",
                                                  {"num_switches": number_of_switches,
                                                   "num_hosts_per_switch": hps},
                                                  conf_root="configurations/",
                                                  synthesis_name="SynthesizeQoS",
                                                  synthesis_params={"same_output_queue": same_output_queue},
                                                  flow_specs=flow_specs,
                                                  topo_link_params=topo_link_params,
                                                  number_of_RT_flows=number_of_RT_flows,
                                                  number_of_BE_flows=number_of_BE_flows,
                                                  test_case_id=test_case+1)

                        nc_list.append(nc)

    return nc_list


def get_forward_reverse_flow(measurement_rates, cap_rate, indx, nxtindx, flow_match, delay_budget, tests_duration, tag):
    # generate random bw_requirements
    current_flow_measurement_rates = []
    for j in range(len(measurement_rates)):
        current_flow_measurement_rates.append(random.randint(1, measurement_rates[j]))

    current_flow_cap_rate = cap_rate + max(current_flow_measurement_rates)

    src = "h" + str(indx[0]) + str(indx[1])
    dst = "h" + str(nxtindx[0]) + str(nxtindx[1])

    forward_flow = FlowSpecification(src_host_id=src,
                                     dst_host_id=dst,
                                     configured_rate=current_flow_cap_rate,
                                     flow_match=flow_match,
                                     measurement_rates=current_flow_measurement_rates,
                                     tests_duration=tests_duration,
                                     delay_budget=delay_budget,
                                     tag=tag)

    reverse_flow = FlowSpecification(src_host_id=dst,
                                     dst_host_id=src,
                                     configured_rate=current_flow_cap_rate,
                                     flow_match=flow_match,
                                     measurement_rates=[],
                                     tests_duration=tests_duration,
                                     delay_budget=delay_budget,
                                     tag=tag)

    return forward_flow, reverse_flow


def prepare_flow_specifications(measurement_rates, tests_duration, number_of_switches, hps, number_of_RT_flows,
                                number_of_BE_flows, delay_budget, cap_rate):

    flow_specs = []

    flow_match = Match(is_wildcard=True)
    flow_match["ethernet_type"] = 0x0800

    flowlist = list(itertools.product(range(1, number_of_switches+1), range(1, hps+1)))

    # for real-time flows
    index_list = random.sample(range(len(flowlist)), number_of_RT_flows + 1) # for real-time flows

    for i in range(number_of_RT_flows):
        indx = flowlist[index_list[i]]
        rnd = range(1, indx[0]) + range(indx[0]+1, number_of_switches+1)
        nxtindx = (random.choice(rnd), random.randint(1, hps))

        #nxtindx = flowlist[index_list[i+1]]

        forward_flow, reverse_flow = get_forward_reverse_flow(measurement_rates, cap_rate, indx, nxtindx, flow_match,
                                                              delay_budget, tests_duration, "real-time")

        flow_specs.append(forward_flow)
        flow_specs.append(reverse_flow)

    # for best-effort flows
    index_list = random.sample(range(len(flowlist)), number_of_BE_flows + 1)  # for best-effort flows

    for i in range(number_of_BE_flows):
        indx = flowlist[index_list[i]]
        rnd = range(1, indx[0]) + range(indx[0] + 1, number_of_switches + 1)
        nxtindx = (random.choice(rnd), random.randint(1, hps))

        #nxtindx = flowlist[index_list[i + 1]]

        forward_flow, reverse_flow = get_forward_reverse_flow(measurement_rates, cap_rate, indx, nxtindx, flow_match,
                                                              delay_budget, tests_duration, "best-effort")

        flow_specs.append(forward_flow)
        flow_specs.append(reverse_flow)

    return flow_specs


def main():

    num_iterations = 5

    tests_duration = 10
    measurement_rates = [5]  # generate a random number between [1,k] (MBPS)
    cap_rate = 0.1

    num_hosts_per_switch_list = [2]
    same_output_queue_list = [False]

    # number_of_RT_flow_list = [2, 4, 6, 8]
    # number_of_RT_flow_list = [3]
    #number_of_BE_flow_list = [3, 0]
    number_of_BE_flow_list = [3]
    # number_of_RT_flow_list = [5, 4]
    number_of_RT_flow_list = [7, 6, 5, 4, 3, 2]  # added for RTSS17 experiments

    number_of_switches = 5

    number_of_test_cases = 25  # number of experimental samples we want to examine

    #base_delay_budget = 0.000025  # in second (25us) (this is end-to-end requirement - netperf gives round trip)
    # base_delay_budget = 0.000100  # in second (100us) (this is end-to-end requirement - netperf gives round trip)
    # RTSS CAM-READY
    # base_delay_budget = 0.000030  # in second (30*diameter = 120 us) (this is end-to-end requirement - netperf gives round trip)
    base_delay_budget = 0.000010  # in second (10*diameter = 40 us) (this is end-to-end requirement - netperf gives round trip)
    # link_delay_upper_bound = 125  # in us, generate random delay between [k/5,k] (us)
    # link_delay_upper_bound = 30  # in us, generate random delay between [k-5, k] (us)
    link_delay_upper_bound = 5  # in us

    topo_link_params = {'bw': 10, 'delay': str(link_delay_upper_bound) + 'us'}  # BW in MBPS

    network_configurations = prepare_network_configurations(num_hosts_per_switch_list,
                                                            same_output_queue_list,
                                                            measurement_rates,
                                                            tests_duration,
                                                            topo_link_params,
                                                            base_delay_budget,
                                                            number_of_switches,
                                                            number_of_RT_flow_list,
                                                            number_of_BE_flow_list,
                                                            number_of_test_cases,
                                                            cap_rate)

    exp = QosDemo(num_iterations, network_configurations, len(measurement_rates), measurement_rates,
                  number_of_test_cases,
                  number_of_RT_flow_list,
                  number_of_BE_flow_list,
                  base_delay_budget,
                  link_delay_upper_bound)

    exp.trigger()

if __name__ == "__main__":
    main()
