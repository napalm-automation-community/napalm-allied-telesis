"""NAPALM Allied Telesis AWPlus."""
# Copyright 2015 Spotify AB. All rights reserved.
#
# The contents of this file are licensed under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with the
# License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.
#import copy
#import functools
#import os
import re
import socket
#import telnetlib
#import tempfile
#import uuid
#from collections import defaultdict

#from netaddr import IPNetwork
#from netaddr.core import AddrFormatError
#from netmiko import FileTransfer, InLineTransfer

#import napalm.base.constants as C
import napalm.base.helpers
from napalm.base.base import NetworkDriver
from napalm.base.exceptions import (
#	ReplaceConfigException,
#	MergeConfigException,
	ConnectionClosedException,
#	CommandErrorException,
	)
from napalm.base.helpers import (
#	canonical_interface_name,
#	transform_lldp_capab,
	textfsm_extractor,
#	split_interface,
#	abbreviated_interface_name,
#	generate_regex_or,
#	sanitize_configs,
	)
from napalm.base.netmiko_helpers import netmiko_args
from napalm_alliedtelesis.constants import LLDP_CAPAB_TRANFORM_TABLE

# Easier to store these as constants
HOUR_SECONDS = 3600
DAY_SECONDS = 24 * HOUR_SECONDS
WEEK_SECONDS = 7 * DAY_SECONDS
YEAR_SECONDS = 365 * DAY_SECONDS


# STD REGEX PATTERNS
IP_ADDR_REGEX = r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"
IPV4_ADDR_REGEX = IP_ADDR_REGEX



class AlliedTelesisDriver(NetworkDriver):
	def __init__(self, hostname, username, password, timeout=60, optional_args=None):
		"""NAPALM AlliedTelesis Handler."""
		if optional_args is None:
			optional_args = {}
		self.hostname = hostname
		self.username = username
		self.password = password
		self.timeout = timeout
		self.platform = "alliedtelesis"
		self.transport =  optional_args.get("transport", "ssh")
		self.transport = "ssh"
		self.netmiko_optional_args = netmiko_args(optional_args)
		default_port = {"ssh": 22 }
		self.netmiko_optional_args.setdefault("port", default_port[self.transport])

	def _send_command(self, command):
		"""Wrapper for self.device.send.command().
		If command is a list will iterate through commands until valid command.
		"""
		try:
			if isinstance(command, list):
				for cmd in command:
					output = self.device.send_command(cmd, expect_string=r"#")
					if "% Invalid" not in output:
						break
			else:
				output = self.device.send_command(command, expect_string=r"#")
			return output
		except (socket.error, EOFError) as e:
			raise ConnectionClosedException(str(e))

	def open(self):
		""" Open a connection to the device."""
		device_type="allied_telesis_awplus"
		self.device = self._netmiko_open(
		    device_type, netmiko_optional_args=self.netmiko_optional_args
		)
    
	def close(self):
		"""Close the connection to the device."""
		self._netmiko_close()

	def is_alive(self):
		"""Returns a flag with the state of the connection."""
		null = chr(0)
		if self.device is None:
			return {"is_alive": False}
		try:
			self.device.write_channel(null)
			return {"is alive": self.device.remote_conn.transport.is_active()}
		except ( socket.error, EOFError ):
			return {"is alive": False }
		

	@staticmethod
	def parse_uptime(uptime_str):
		found=re.match("(\\d+) days (..:..:..)",uptime_str)
		if found:
			days=found.group(1)
			hour,minutes,second=found.group(2).split(":")
			uptime_sec = (
				(int(days) * DAY_SECONDS )
				+ ( int(hour) * 3600 )
				+ ( int(minutes) * 60)
				+ int(second)
				)
		return uptime_sec

	def get_facts(self):
		"""Return a set of facts from the devices."""
		vendor="Allied Telesis"
		uptime = -1
		serial_number, fqdn, os_version, hostname, domain_name = ("Unknown",) * 5
		show_ver = self._send_command("show system")
		show_hosts = self._send_command("show hosts")
		show_interface = self._send_command("show interface brief")
		stack_regex=r"(Stack member 1)(.*)(?=Stack member)"
		system_regex=r"(?<=System Name\n).*(?=\nSystem Contact)"
		version_regex=r"Current software\s+:\s(\S+)"
		stack_area=re.search(stack_regex,show_ver, re.MULTILINE | re.DOTALL)
		stack=stack_area.group(2).split("\n")
		for line in stack:
	# uptime/serial_number
	# Uptime	     : 1 days 17:36:04
			if "Uptime " in line:
				uptime_str = line.split(": ",1)[1]
				uptime = self.parse_uptime(uptime_str)
			if "Base" in line:
				found=re.match("\\w+\\s+\\d+\\s+\\w+\\s+(\\S+\\s?\\S+?)\\s+\\S+\\s+(\\S+)",line)
				if found:
					serial_number=found.group(2)
					model=found.group(1)
		found=re.search(version_regex, show_ver)
		if found:
			os_version=found.group(1)

	# find Hostname
		host_found=re.search(system_regex,show_ver,  re.MULTILINE | re.DOTALL)
		if host_found:
			hostname=host_found.group().split()[0]

	# Determine domain_name and fqdn
		for line in show_hosts.splitlines():
			if "Default domain" in line:
				_, domain_name = line.split("Default domain is ")
				domain_name = domain_name.strip()
				break
		if domain_name != "not set" and hostname != "Unknown":
			fqdn = "{}.{}".format(hostname, domain_name)
	
	# Interfaces
		interface_list = []
		for line in show_interface.splitlines():
			if "Interface " in line:
				continue
			interface = line.split()[0]
	#if interface.startswith("port"):
			interface_list.append(interface)

		return {
			"uptime": uptime,
			"vendor": vendor,
			"os_version": str(os_version),
			"serial_number": str(serial_number),
			"model": str(model),
			"hostname": str(hostname),
			"fqdn": fqdn,
			"interface_list": interface_list,
				}

	def get_interfaces(self):
		""" Get the Interfaces """
		
		interface = {}
		command = "show interface"
		output = self._send_command(command)
		interface_entries = textfsm_extractor( self, "show_interface", output)
		for idx, interface_entry in enumerate(interface_entries):
			local_intf = interface_entry.pop("interface")
			if interface_entry["mac_address"]:
				interface_entry["mac_address"] = napalm.base.helpers.mac(interface_entry["mac_address"])
			if interface_entry["last_flapped"]:
				last_flapped= interface_entry["last_flapped"]
				interface_entry["last_flapped"] = self.parse_uptime(last_flapped)
			interface.setdefault(local_intf, [])
			interface[local_intf].append(interface_entry)
		return interface




	def get_environment(self):
		"""
		Get the CPU 5 Minutes Average
		First CPU is from Stack1, Second from Stack2, ..
		All Others only from the First Stack
		"""
		environment= {"fans": {}, "temperature": {}, "power": {}, "cpu": {}, "memory": {}}
		cpu_cmd = "show cpu"
		mem_cmd = "show memory"
		temp_cmd = "show system environment"
		cpu_regex=r"\s5 minutes:\s(\d+\.\d+)"
#		resource_id_regex=r"Resource\sID:\s\d+\s+Name:\s.*?(?=^Resource\sID:\s\d+\s+Name:\s|\Z)"
		output = self._send_command(cpu_cmd)
		stack_regex=r"Stack member \d.*?(?=^Stack member|\Z)"
		env_regex=r"Resource\sID:\s\d+\s+Name:\s.*?(?=^Resource\sID:\s\d+\s+Name:\s|\Z)"
#	 psu_regex=r"\d+\s+PSU Power Output\s+\(\S+)\s\S\s\S\s(\S+)"
		psu_regex=r".*PSU Power Output\s+\S+\s+\S+\s+\S+\s+(\S+)"
		psu_name_regex=r".*Name:\s+(\S+\s?\d?)"
		temp_cpu_regex=r"\d+\s+Temp:\s(\S+)\s\(Degrees\sC\)\s+(\d+)\s+\S+\s+\d+\s+(\S+)"
		temp_fans_regex=r"\d+\s+Fan:\s(\S+\s\d+)\s\(Rpm\)\s+\S+\s+\S+\s+\S+\s+(\S+)"
		mem_regex=r"Stack member 1:\n\n(?=RAM total:).*?(\d+)\s\S+\s\S+:\s(\d+)\s\S+\s\S+\s(\d+)\s\S+"
		cpus=re.findall(cpu_regex,output)
		if len(cpus) > 1:
			for (i, value ) in enumerate(cpus,start=0):
				environment["cpu"][i] = {}
				environment["cpu"][i]["%usage"] = float(value)
		else:
			environment["cpu"][0] = {}
			environment["cpu"][0]["%usage"] = float(cpus)

		output=self._send_command(temp_cmd)
		stacks=re.findall(stack_regex,output,re.DOTALL|re.MULTILINE)
		stack1=re.findall(env_regex,stacks[0],re.DOTALL|re.MULTILINE)
		for resource in stack1:
			psu_temp=re.search(psu_name_regex,resource)
			psu_name=psu_temp.group(1)
			if psu_name.startswith("PSU"):
				psu=re.match(psu_regex,resource,re.DOTALL|re.MULTILINE)
				if psu.group(1) == "Ok":
					status = True
				else:
					status = False
				environment["power"][psu_name]={"capacity": "370.0","output": "0.0", "status": status}
			else:
				for temp in re.finditer(temp_cpu_regex,resource):
					if temp.group(3) == "Ok":
						status = False
					else:
						status = True
					environment["temperature"][temp.group(1)]={"temperature": temp.group(2), "status": status}
				for temp in re.finditer(temp_fans_regex,resource):
					if temp.group(2) == "Ok":
						status = True
					else:
						status = False
					environment["fans"][temp.group(1)]= {"status": status}
		output=self._send_command(mem_cmd)
		tmp_mem=re.search(mem_regex,output,re.MULTILINE)
		if tmp_mem:
			mem_total=int(tmp_mem.group(1))
			mem_free=int(tmp_mem.group(2))
#			mem_buffers=int(tmp_mem.group(3))
			mem_used=mem_total - mem_free
			environment["memory"]["used_ram"] = mem_used
			environment["memory"]["available_ram"] = mem_total
		return environment

	def get_arp_table(self, vrf=""):
		"""Return the ARP table."""
		if vrf:
			msg = "VRF support has not been added for this getter on this platform."
			raise NotImplementedError(msg)

		arp_table = []
		arp_cmd="show arp"
		arp_regex=r"(\d+\.\d+\.\d+\.\d+)\s+(\S+)\s+(\S+\s?\S+?)\s+(\S+)\s+(\S+)"
		output=self._send_command(arp_cmd)
		arp_match=re.findall(arp_regex,output)
		for arp in arp_match:
			arp_entry = {"interface": arp[2] ,
			"mac" : napalm.base.helpers.mac(arp[1]),
			"ip" : napalm.base.helpers.ip(arp[0]),
			"age": "-1.0"}
			arp_table.append(arp_entry)
		return arp_table

#	 for line in output.splitlines():
#	     if "IP Address" in line:
#		 continue
#	     ip,mac,interface,port,type = line.split()
#	     arp_entry = {"interface": interface }
#	     arp_entry["mac"] = napalm.base.helpers.mac(mac)
#	     arp_entry["ip"] = napalm.base.helpers.ip(ip)
#	     arp_entry["age"] = "-1.0"
#	     arp_table.append(arp_entry)
#	 return arp_table

	def get_lldp_neighbors(self):
		"""Allied implementation of get_lldp_neighbors."""
		lldp = {}
		neighbors_detail = self.get_lldp_neighbors_detail()
		for intf_name, entries in neighbors_detail.items():
			lldp[intf_name] = []
			for lldp_entry in entries:
				hostname = lldp_entry["remote_system_name"]
				# Match IOS behaviour of taking remote chassis ID
				# When lacking a system name (in show lldp neighbors)
				if not hostname:
					hostname = lldp_entry["remote_chassis_id"]
				lldp_dict = {"port": lldp_entry["remote_port"], "hostname": hostname}
				lldp[intf_name].append(lldp_dict)
		return lldp

	def _transform_lldp_capab(self, capabilities):
		if capabilities and isinstance(capabilities, str):
			capabilities = capabilities.strip().lower().split(",")
			return sorted(
				[LLDP_CAPAB_TRANFORM_TABLE[c.strip()] for c in capabilities]
				)
		else:
			return []

	def get_lldp_neighbors_detail(self,  interface=""):
		""" Allied Telesis Implementation of get_lldp_neighbors_detail."""
		lldp = {}
		if interface:
			command = "show lldp neighbors {} detail".format(interface)
		else:
			command = "show lldp neighbors detail"
		lldp_entries = self._send_command(command)
		lldp_entries = textfsm_extractor( self, "show_lldp_neighbors_detail", lldp_entries)
		if len(lldp_entries) == 0:
			return {}

		for idx, lldp_entry in enumerate(lldp_entries):
			local_intf = lldp_entry.pop("local_interface")
			for field in lldp_entry:
				if "[not advertised]" in lldp_entry[field]:
					lldp_entry[field] = ""
			lldp_entry["remote_system_description"] = " ".join([str(x) for x in lldp_entry["remote_system_description"]])

			""" Cause {'remote_chassis_id': '38353738-3833-5A43-4A38-323130333443', 
			Test if "." in remote_chassis_id"""

			if "." in lldp_entry["remote_chassis_id"]:
				lldp_entry["remote_chassis_id"] = napalm.base.helpers.mac(lldp_entry["remote_chassis_id"])
			lldp_entry["parent_interface"] = ""
			lldp_entry["remote_system_capab"]=self._transform_lldp_capab(lldp_entry["remote_system_capab"])
			lldp_entry["remote_system_enable_cabap"] =self._transform_lldp_capab(lldp_entry["remote_system_enable_cabap"])
			lldp.setdefault(local_intf, [])
			lldp[local_intf].append(lldp_entry)
		return lldp


	def get_optics(self):
		pass

	def get_interfaces_ip(self):
		""" Only IPv4
		No Data for IPv6
		"""
		interfaces = {}
		command = "show ip interface"
		show_ip_interface = self._send_command(command)
#		command = "show ipv6 interface"
#		show_ipv6_interface = self._send_command(command)
		INTERNET_ADDRESS = r"\S+\s+(?P<ip>{})/(?P<prefix>\d+).*".format(IPV4_ADDR_REGEX)
		for line in show_ip_interface.splitlines():
			if "IP-Address" in line or "unassigned" in line:
				continue
			if line[0] != " ":
				ipv4 = {}
				interface_name = line.split()[0]
			m = re.match(INTERNET_ADDRESS, line)
			if m:
				ip, prefix = m.groups()
				ipv4.update({ip: {"prefix_length": int(prefix)}})
				interfaces[interface_name] = {"ipv4": ipv4}

		return interfaces
		

	def get_vlans(self):
		vlans={}
		command="show vlan all"
		pass

