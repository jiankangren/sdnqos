__author__ = 'Monowar Hasan'

from mininet.topo import Topo
import random


class RandomTopoWithParams(Topo):
    
    def __init__(self, params, linkopts):
        
        Topo.__init__(self)
        
        self.params = params
        self.total_switches = self.params["num_switches"]
        self.switch_names = []

        self.link_params = []

        #  Add switches and hosts under them
        for i in xrange(self.params["num_switches"]):
            curr_switch = self.addSwitch("s" + str(i+1), protocols="OpenFlow14")
            self.switch_names.append(curr_switch)

            for j in xrange(self.params["num_hosts_per_switch"]):
                curr_switch_host = self.addHost("h" + str(i+1) + str(j+1))
                link_options = self.get_random_link_options(linkopts)
                bw = link_options["bw"]
                delay = '\'{}\''.format(link_options["delay"])

                # self.addLink(curr_switch, curr_switch_host, **link_options)
                self.addLink(curr_switch, curr_switch_host, bw=bw, delay=delay)
                # save the link info
                self.link_params.append({"node1": curr_switch,
                                         "node2": curr_switch_host,
                                         "bw": link_options["bw"],
                                         "delay": link_options["delay"]})

        #  Add links between switches
        if self.params["num_switches"] > 1:
            for i in xrange(self.params["num_switches"] - 1):
                link_options = self.get_random_link_options(linkopts)
                # print link_options

                bw = link_options["bw"]
                delay = '\'{}\''.format(link_options["delay"])

                # self.addLink(self.switch_names[i], self.switch_names[i+1], **link_options)
                self.addLink(self.switch_names[i], self.switch_names[i+1], bw=bw, delay=delay)

                # save the link info
                self.link_params.append({"node1": self.switch_names[i],
                                         "node2": self.switch_names[i+1],
                                         "bw": link_options["bw"],
                                         "delay": link_options["delay"]})

            #  Form a ring only when there are more than two switches
            if self.params["num_switches"] > 2:
                link_options = self.get_random_link_options(linkopts)

                bw = link_options["bw"]
                delay = '\'{}\''.format(link_options["delay"])

                # self.addLink(self.switch_names[0], self.switch_names[-1], **link_options)
                self.addLink(self.switch_names[0], self.switch_names[-1], bw=bw, delay=delay)

                # save the link info
                self.link_params.append({"node1": self.switch_names[0],
                                         "node2": self.switch_names[-1],
                                         "bw": link_options["bw"],
                                         "delay": link_options["delay"]})

                # create some random links
                nodelist = self.noncontiguoussample(self.params["num_switches"]-1, int(self.params["num_switches"]/2.0))

                for i in range(len(nodelist)-1):
                    self.switch_names[nodelist[i]]

                    link_options = self.get_random_link_options(linkopts)

                    bw = link_options["bw"]
                    delay = '\'{}\''.format(link_options["delay"])

                    # self.addLink(self.switch_names[nodelist[i]], self.switch_names[nodelist[i+1]], **link_options)
                    self.addLink(self.switch_names[nodelist[i]], self.switch_names[nodelist[i + 1]], bw=bw, delay=delay)
                    # save the link info
                    self.link_params.append({"node1": self.switch_names[nodelist[i]],
                                             "node2": self.switch_names[nodelist[i+1]],
                                             "bw": link_options["bw"],
                                             "delay": link_options["delay"]})

    def get_random_link_options(self, linkopts):
        delay = int(linkopts["delay"].replace('us', ''))
        #delay = float(linkopts["delay"].replace('ms', ''))
        # delay = str(random.randint(1, delay)) + 'ms'
        #delay = str(random.uniform(0, delay)) + 'ms'
        #delay = str(random.uniform(delay/100, delay)) + 'us'
        #delay = str(random.randint(delay/5, delay)) + 'us'
        # delay = str(random.randint(delay - 5, delay)) + 'us'  # RTSS camera ready
        delay = str(delay) + 'us'  # RTSS camera ready

        link_options = {'bw': linkopts['bw'], 'delay': delay}
        return link_options

    def get_switches_with_hosts(self):
        return self.switch_names

    def __str__(self):
        params_str = ''
        for k, v in self.params.items():
            params_str += "_" + str(k) + "_" + str(v)
        return self.__class__.__name__ + params_str

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
