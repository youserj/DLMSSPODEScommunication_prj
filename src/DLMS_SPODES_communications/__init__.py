from .network import Network, AsyncNetwork
from .ble import BLE
from .serial_port import SerialPort, RS485
# import argparse
import sys


def call_script(args=sys.argv):
    for i, arg in enumerate(args):
        print(f'Arg #{i}: {arg}')
    # parser = argparse.ArgumentParser(description="hello")
    # parser.add_argument('target', type=str, help='the name of the target')
    # parser.add_argument('--end', dest='end', default="!",
    #                     help='sum the integers (default: find the max)')
    # args = parser.parse_args()
