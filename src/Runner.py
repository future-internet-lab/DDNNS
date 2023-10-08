from src.Logging import *
from src.Data import Data
from src.Model import Model
from src.Optim import Optim
from src.Utils import *


class Runner:
    def __init__(self, model: Model, data: Data, opt: Optim):
        self.model = model
        self.data = data
        self.opt = opt
        self.time = 0.0

        # format event queue: time, action, data_size,
        self.event_queue = []

    def insert_dev_event(self, time: float, action: str, name: str, data_size: int, flow: str):
        data = {'time': time, 'action': action, 'type': 'D', 'name': name, 'data_size': data_size, 'flow': flow}
        self.event_queue.append(data)
        self.event_queue.sort(key=timer)
        self.time = time
        log.info(data)

    def insert_link_event(self, time: float, action: str, _from: str, _to: str, data_size: int, flow: str):
        data = {'time': time, 'action': action, 'type': 'L', 'from': _from, 'to': _to, 'data_size': data_size,
                'flow': flow}
        self.event_queue.append(data)
        self.event_queue.sort(key=timer)
        self.time = time
        log.info(data)

    def start(self):
        log.warn("Start run simulation")
        trained_data = 0
        while trained_data <= self.data.num_data:
            # start initial with input data devices
            for a in self.model.input_devices:
                if not self.model.devices_graph.nodes[a]["handler"]:
                    log.info(f"Insert input data on device {a}")
                    data_size = self.opt.batch_size / len(self.model.input_devices)
                    self.insert_dev_event(self.time, 'start', a, int(data_size), "F")
                    self.model.devices_graph.nodes[a]["handler"] = True
                    # backward when reaches end device
                # add wait event for handler = True ...

            # handler event (event name means handler after this event)
            self.handler_event()

            # and now start backpropagation
            for a in self.model.output_device:
                if not self.model.devices_graph.nodes[a]["handler"]:
                    log.info(f"Start backpropagation on device {a}")
                    data_size = self.opt.batch_size / len(self.model.input_devices)
                    self.model.devices_graph.nodes[a]["handler"] = True
                    self.insert_dev_event(self.time, 'start', a, int(data_size), "B")

            self.handler_event()

                # end transfer -> run direction devices
            trained_data = self.data.num_data + 1  # for test

    def handler_event(self):
        while len(self.event_queue) != 0:
            event = self.event_queue.pop(0)
            if event['type'] == 'D':
                dev = event['name']
                time = event['time']
                data_size = event['data_size']
                node_dev = self.model.devices_graph.nodes[dev]

                # start training event
                if event['action'] == 'start':
                    training_rate = node_dev['training_rate']
                    exec_time = self.model.get_exec_time(dev)
                    # TODO: check resource
                    self.model.devices_graph.nodes[dev]["handler"] = False
                    self.insert_dev_event(time + training_rate * exec_time * (1 + generate_normal_random()), 'end',
                                          dev, int(data_size), event['flow'])
                    node_dev['handler'] = False

                # end training event -> transfer
                elif event['action'] == 'end':
                    # TODO: check resource
                    # TODO: add busy wait
                    next_dev = None
                    if event['flow'] == "F" and dev not in self.model.output_device:
                        next_dev = node_dev['next_dev']
                    elif event['flow'] == "B" and dev not in self.model.input_devices:
                        next_dev = node_dev['prev_dev']
                    if next_dev is not None:
                        for n_dev in next_dev:
                            self.model.devices_graph[dev][n_dev]["handler"] = True
                            self.insert_link_event(time, 'start', dev, n_dev, int(data_size / len(next_dev)),
                                                   event['flow'])

            # start transfer
            elif event['type'] == 'L':
                from_dev = event['from']
                to_dev = event['to']
                time = event['time']
                data_size = event['data_size']

                # link start receive data
                if event['action'] == 'start':
                    data_rate_time = self.model.get_trans_time(from_dev, to_dev, event['flow'])
                    delta = (data_rate_time * (1 + generate_normal_random()) * 1_000 * data_size) / \
                            (self.data.size * self.opt.batch_size)
                    # assume that root data gain 1_000 ms
                    self.model.devices_graph[from_dev][to_dev]["handler"] = False
                    self.insert_link_event(time + delta, 'end', from_dev, to_dev, int(data_size), event['flow'])

                # link done transmission
                elif event['action'] == 'end':
                    # TODO: add busy wait
                    self.model.devices_graph.nodes[to_dev]["handler"] = True
                    self.insert_dev_event(time, 'start', to_dev, int(data_size), event['flow'])