import subprocess
import os

class ControllerMan(object):
    def __init__(self,  controller):
        self.controller = controller

        if controller == "odl":
            raise NotImplemented

        elif controller == "ryu":
            self.ryu_proc = None

        elif controller == "sel":
            raise NotImplemented

    def start_controller(self):
        if self.controller == "odl":
            raise NotImplemented
        elif self.controller == "sel":
            raise NotImplemented
        elif self.controller == "ryu":
            # ryu_cmd = ["ryu-manager", "--observe-links", "ryu.app.ofctl_rest", "ryu.app.rest_topology"]
            # self.ryu_proc = subprocess.Popen(ryu_cmd, stdout=subprocess.PIPE)
            os.system("ryu-manager --observe-links ryu.app.ofctl_rest ryu.app.rest_topology&")
            return 6633

    def stop_controller(self):

        if self.controller == "ryu":
            # self.ryu_proc.kill()
            # subprocess.Popen.wait(self.ryu_proc)
            os.system("sudo pkill ryu-manager")

        elif self.controller == "sel":
            pass
        else:
            raise NotImplemented


