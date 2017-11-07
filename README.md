# sdnqos


## Setup instructions

- If you don't have pip installed, then install the python package manager. (Ubuntu package: python-pip)
- Ensure that OVS version 2.3.0 is installed.
- sudo pip install ryu==4.0
- sudo pip install networkx
- sudo pip install netaddr
- sudo pip install intervaltree
- sudo pip install httplib2
- Install mininet version 2.2 by following instructions here: http://mininet.org/download/
- sudo apt-get install python-scipy
- sudo apt-get install python-numpy
- sudo apt-get install python-matplotlib
- Setup PYTHONPATH to src folder by adding following to ~/.bashrc: export PYTHONPATH=${PYTHONPATH}:/home/flow/qos_synthesis/src/ and allow PYTHONPATH to be retained by sudo by adding following to /etc/sudoers: Defaults env_keep += "PYTHONPATH"


- Install netperf from its source (http://www.netperf.org/netperf/DownloadNetperf.html) with following compile options enabled(./configure --enable-intervals --enable-burst --enable-demo --enable-omni)