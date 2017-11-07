#__author__ = 'Monowar Hasan'

from __future__ import division
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
                 base_delay_budget_list,
                 link_delay_upper_bound):

        super(QosDemo, self).__init__("number_of_hosts", num_iterations)
        self.network_configurations = network_configurations
        self.num_measurements = num_measurements

        self.measurement_rates = measurement_rates

        self.number_of_test_cases = number_of_test_cases
        self.number_of_RT_flow_list = number_of_RT_flow_list
        self.number_of_BE_flow_list = number_of_BE_flow_list

        self.base_delay_budget_list = base_delay_budget_list
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

        self.shed_count = defaultdict(dict)

    def init_output_result_dictonary(self):

        for number_of_RT_flows in self.number_of_RT_flow_list:
                for delay_budget in self.base_delay_budget_list:
                    self.shed_count[number_of_RT_flows][delay_budget] = 0

    def trigger(self):

        self.init_output_result_dictonary()
        time.sleep(5) # sleep for a while if ryu or anything needs some time
        os.system("pkill ryu-manager")  # cleanup

        print "Experiment starting..."

        for nc in self.network_configurations:
            #print "network_configuration:", nc
            print "######################################"
            print "#of flow: {}, delay: {}, iteration: {}".format(nc.number_of_RT_flows,
                                                                  nc.min_delay_budget_for_all_flows, nc.test_case_id)
            print "######################################"

            #nc.setup_network_graph(mininet_setup_gap=1, synthesis_setup_gap=1)
            nc.setup_network_graph_without_mininet()

            # nc.init_flow_specs()
            nc.calibrate_delay(nc.min_delay_budget_for_all_flows)

            # mhasan: MCP code will go there
            # mcph.print_delay_budget(nc)

            mcph.find_path_by_mcp(nc)  # update the path in 'path' variable of FlowSpecification

            if not mcph.test_all_flow_is_schedulable(nc):
                print "Network configuration is NOT feasible (no path found)!"
                nc.isFeasible = False
                #continue
            else:
                print "Network configuration is feasible (path found for all flows)!"
                nc.isFeasible = True

                # increase schedulability count
                self.shed_count[nc.number_of_RT_flows][nc.min_delay_budget_for_all_flows] += 1
                # nc.cleanup_mininet()
                # os.system("pkill mn")  # cleanup
                # os.system("pkill ryu-manager")  # cleanup


        self.write_data_to_file('schedulability_traces.pickle')
        #print self.shed_count
        print "Experiment Done!"

    def get_minimum_diameter(self):

        # return minimum diameter from all the network configurations
        mindia = float('Inf')
        for nc in self.network_configurations:
            if mindia > nc.network_diameter:
                mindia = nc.network_diameter
        return mindia

    def write_data_to_file(self, filename):

        # save data to workspace for plotting
        print "Writing data as pickle object..."
        with open(filename, 'w') as f:
            pickle.dump([self.number_of_RT_flow_list,
                         self.number_of_test_cases,
                         self.base_delay_budget_list,
                         self.shed_count,
                         self.get_minimum_diameter()], f)


def prepare_network_configurations(num_hosts_per_switch_list,
                                   same_output_queue_list, measurement_rates, tests_duration,
                                   topo_link_params, delay_budget_list,
                                   number_of_switches,
                                   number_of_RT_flow_list,
                                   number_of_BE_flow_list,
                                   test_case_list,
                                   cap_rate
                                   ):
    nc_list = []

    hps = num_hosts_per_switch_list[0]
    same_output_queue = False

    for number_of_RT_flows in number_of_RT_flow_list:
        for number_of_BE_flows in number_of_BE_flow_list:
            for delay_budget in delay_budget_list:
                for test_case in range(test_case_list):
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
                                              test_case_id=test_case + 1
                                              )

                    nc.min_delay_budget_for_all_flows = delay_budget  # use this way for compatibility with prev. code

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
    # if unique number (e.g. unique flow-per host) required
    # index_list = random.sample(range(len(flowlist)), number_of_RT_flows + 1) # for real-time flows

    # generate random indices (#of_RT_flows)
    index_list = [random.randint(0, len(flowlist) - 1) for i in range(number_of_RT_flows)]

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
    measurement_rates = [10]  # generate a random number between [1,k] (MBPS)
    cap_rate = 0.1

    num_hosts_per_switch_list = [2]
    same_output_queue_list = [False]

    # number_of_RT_flow_list = [2, 4, 6, 8]
    # number_of_RT_flow_list = [2, 3]
    number_of_BE_flow_list = [0]
    # number_of_RT_flow_list = [8, 7, 6, 5, 4, 3, 2, 1]
    number_of_RT_flow_list = [2, 4, 6, 8, 10, 15, 20]  # added for RTSS17

    number_of_switches = 5

    number_of_test_cases = 250  # number of experimental samples we want to examine

    #base_delay_budget = 0.000025  # in second (25us) (this is end-to-end requirement - netperf gives round trip)
    #base_delay_budget = 0.000050  # in second (50us) (this is end-to-end requirement - netperf gives round trip)

    # in second (25-125us) (this is end-to-end requirement - netperf gives round trip)
    #base_delay_budget_list = [0.000010, 0.000015, 0.000020, 0.000025, 0.000050, 0.000075, 0.000100, 0.000125]

    base_delay_budget_list = [0.000010, 0.000015, 0.000020, 0.000025, 0.000050, 0.000075, 0.000100, 0.000125, 0.000150,
                              0.000250, 0.000500]  # added for RTSS17

    # added for RTSS cam
    base_delay_budget_list = [i/5 for i in base_delay_budget_list]  # added for RTSS17

    # base_delay_budget_list = [0.000005, 0.000010, 0.000015, 0.000020, 0.000025, 0.000050, 0.000075, 0.000100,
    #                           0.000125, 0.000150, 0.000250]  # added for RTSS17 CAM

    # link_delay_upper_bound = 125  # in us, generate random delay between [k/5,k] (us)
    link_delay_upper_bound = 25  # in us, generate random delay between [k/5,k] (us)  ## FOR RTSS CAM

    topo_link_params = {'bw': 10, 'delay': str(link_delay_upper_bound) + 'us'}  # BW in MBPS

    network_configurations = prepare_network_configurations(num_hosts_per_switch_list,
                                                            same_output_queue_list,
                                                            measurement_rates,
                                                            tests_duration,
                                                            topo_link_params,
                                                            base_delay_budget_list,
                                                            number_of_switches,
                                                            number_of_RT_flow_list,
                                                            number_of_BE_flow_list,
                                                            number_of_test_cases,
                                                            cap_rate)

    exp = QosDemo(num_iterations, network_configurations, len(measurement_rates), measurement_rates,
                  number_of_test_cases,
                  number_of_RT_flow_list,
                  number_of_BE_flow_list,
                  base_delay_budget_list,
                  link_delay_upper_bound)

    exp.trigger()

if __name__ == "__main__":
    main()
