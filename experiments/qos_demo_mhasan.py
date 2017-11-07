__author__ = 'Monowar Hasan'

import sys
import os
import time
from collections import defaultdict

sys.path.append("./")


from controller_man import ControllerMan
from experiment import Experiment
from network_configuration import NetworkConfiguration
from flow_specification import FlowSpecification
from model.match import Match

# mhasan import
#from mcp_helper import MCP_Helper
import mcp_helper as mcph


class QosDemo(Experiment):

    def __init__(self,
                 num_iterations,
                 network_configurations,
                 num_measurements):

        super(QosDemo, self).__init__("number_of_hosts", num_iterations)
        self.network_configurations = network_configurations
        self.num_measurements = num_measurements

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

            # mhasan: MCP code will go there
            mcph.find_path_by_mcp(nc)  # update the path in 'path' variable of FlowSpecification
            mcph.synthesize_flow_specifications(nc)
            # nc.mininet_obj.pingAll('1')
            self.measure_flow_rates(nc)

        print "here"


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

                for fs in nc.flow_specs:

                    if not fs.measurement_rates:
                        continue

                    os.system('killall netserver') # kill all previous netserver instance

                    server_command = "/usr/local/bin/netserver"
                    server_output = fs.mn_dst_host.cmd(server_command)
                    client_output = fs.mn_src_host.cmd(fs.construct_netperf_cmd_str(fs.measurement_rates[j]))

                    if fs.tests_duration > max_fs_duration:
                        max_fs_duration = fs.tests_duration

                # Sleep for 10 seconds more than flow duration to make sure netperf has finished.
                time.sleep(max_fs_duration + 10)

                for fs in nc.flow_specs:

                    if not fs.measurement_rates:
                        continue

                    print "=== netperf output ==="
                    netperf_output_string = fs.mn_src_host.read()
                    print netperf_output_string
                    if netperf_output_string.find("no response received") >= 0:
                        raise ValueError("No response received from netperf...")

                    fs.measurements[fs.measurement_rates[j]].append(fs.parse_measurements(netperf_output_string))


def prepare_network_configurations(num_hosts_per_switch_list,
                                   same_output_queue_list, measurement_rates, tests_duration,
                                   topo_link_params, delay_budget):
    nc_list = []

    for same_output_queue in same_output_queue_list:

        for hps in num_hosts_per_switch_list:

            flow_specs = prepare_flow_specifications(measurement_rates, tests_duration, delay_budget)

            # mhasan: change with link params
            nc = NetworkConfiguration("ryu",
                                      "ring_with_param",
                                      {"num_switches": 10,
                                       "num_hosts_per_switch": hps},
                                      conf_root="configurations/",
                                      synthesis_name="SynthesizeQoS",
                                      synthesis_params={"same_output_queue": same_output_queue},
                                      flow_specs=flow_specs,
                                      topo_link_params=topo_link_params)

            nc_list.append(nc)

    return nc_list


def prepare_flow_specifications(measurement_rates, tests_duration, delay_budget):

    flow_specs = []

    flow_match = Match(is_wildcard=True)
    flow_match["ethernet_type"] = 0x0800

    #'''
    h41_to_h12 = FlowSpecification(src_host_id="h81",
                                   dst_host_id="h21",
                                   configured_rate=50,
                                   flow_match=flow_match,
                                   measurement_rates=measurement_rates,
                                   tests_duration=tests_duration,
                                   delay_budget=delay_budget)

    h21_to_h41 = FlowSpecification(src_host_id="h21",
                                   dst_host_id="h81",
                                   configured_rate=50,
                                   flow_match=flow_match,
                                   measurement_rates=[],
                                   tests_duration=tests_duration,
                                   delay_budget=delay_budget)

    flow_specs.append(h41_to_h12)
    flow_specs.append(h21_to_h41)
    #'''

    '''
    h1s2_to_h1s1 = FlowSpecification(src_host_id="h1s2",
                                     dst_host_id="h1s1",
                                     configured_rate=50,
                                     flow_match=flow_match,
                                     measurement_rates=measurement_rates,
                                     tests_duration=tests_duration,
                                     delay_budget=delay_budget)

    h2s2_to_h2s1 = FlowSpecification(src_host_id="h2s2",
                                     dst_host_id="h2s1",
                                     configured_rate=50,
                                     flow_match=flow_match,
                                     measurement_rates=measurement_rates,
                                     tests_duration=tests_duration,
                                     delay_budget=delay_budget)

    h1s1_to_h1s2 = FlowSpecification(src_host_id="h1s1",
                                     dst_host_id="h1s2",
                                     configured_rate=50,
                                     flow_match=flow_match,
                                     measurement_rates=[],
                                     tests_duration=tests_duration,
                                     delay_budget=delay_budget)

    h2s1_to_h2s2 = FlowSpecification(src_host_id="h2s1",
                                     dst_host_id="h2s2",
                                     configured_rate=50,
                                     flow_match=flow_match,
                                     measurement_rates=[],
                                     tests_duration=tests_duration,
                                     delay_budget=delay_budget)

    flow_specs.append(h1s2_to_h1s1)
    flow_specs.append(h2s2_to_h2s1)

    flow_specs.append(h1s1_to_h1s2)
    flow_specs.append(h2s1_to_h2s2)
    '''
    return flow_specs


def main():

    num_iterations = 1

    tests_duration = 5
    #measurement_rates = [40, 45, 50]
    measurement_rates = [40]

    num_hosts_per_switch_list = [2]
    same_output_queue_list = [False, True]

    # mhasan: added link param and delay budget
    delay_budget = 0.1  # in second (100ms)
    topo_link_params = {'bw': 1000, 'delay': '3ms'}  # BW in MBPS

    network_configurations = prepare_network_configurations(num_hosts_per_switch_list,
                                                            same_output_queue_list,
                                                            measurement_rates,
                                                            tests_duration,
                                                            topo_link_params,
                                                            delay_budget)

    exp = QosDemo(num_iterations, network_configurations, len(measurement_rates))

    exp.trigger()

if __name__ == "__main__":
    main()