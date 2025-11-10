from netmiko import ConnectHandler
from typing import List, Optional

class NetAgent:
    """
    A class for interacting with network devices in the NetAgents system.
    It provides methods to execute 'show' family commands (for viewing configurations, counters, interfaces, etc.)
    and 'set' family commands (for configuring switches or other devices).
    
    This class uses Netmiko for SSH/Telnet connections to network devices.
    Ensure Netmiko is installed: pip install netmiko
    
    Usage example:
    agent = NetAgent(host='192.168.1.1', username='admin', password='pass', device_type='cisco_ios')
    show_result = agent.execute_show('show running-config')
    set_result = agent.execute_set(['interface GigabitEthernet0/1', 'description Test Interface'])
    agent.disconnect()
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        device_type: str = 'cisco_ios',  # Default to Cisco IOS; can be 'juniper_junos', 'hp_procurve', etc.
        global_delay_factor: str = 2,
        port: int = 22,
        secret: Optional[str] = None,  # Enable secret if required
    ):
        """
        Initialize the NetAgent with connection parameters.
        
        :param host: IP address or hostname of the device.
        :param username: Username for authentication.
        :param password: Password for authentication.
        :param device_type: Type of device (e.g., 'cisco_ios', 'juniper_junos').
        :param port: SSH/Telnet port (default 22).
        :param secret: Enable secret password if needed for privileged mode.
        """
        self.device = {
            'device_type': device_type,
            'global_delay_factor': global_delay_factor,
            'host': host,
            'username': username,
            'password': password,
            'port': port,
            'secret': secret or password,  # Use password as secret if not provided
        }
        self.conn = ConnectHandler(**self.device)
        self.conn.enable()  # Enter privileged mode if possible

    def execute_show(self, command: str) -> str:
        """
        Execute a 'show' family command and return the result.
        
        This is used to view current configurations, counters, active interfaces, etc.
        
        :param command: The show command to execute (e.g., 'show interfaces', 'show running-config').
        :return: The output from the command as a string.
        """
        try:

            hostname = self.conn.find_prompt().split('@')[1].split('#')[0]
            print(f"Connected to {hostname}")

            result = self.conn.send_command(command)
            return result
        except Exception as e:
            return f"Error executing show command: {str(e)}"

    def execute_set(self, commands: List[str]) -> str:
        """
        Execute a 'set' family command (configuration changes) and return the result.
        
        This is used to set configurations on the switch or device.
        Commands are sent in config mode, and changes are committed.
        
        :param commands: A list of configuration commands (e.g., ['interface GigabitEthernet0/1', 'shutdown']).
        :return: The output from the configuration session as a string.
        """
        try:
            self.conn.config_mode()
            result = self.conn.send_config_set(commands)
            self.conn.commit()  # Commit changes if device supports it (e.g., Juniper); otherwise, save config
            self.conn.exit_config_mode()
            # For Cisco-like devices, save the config
            if 'cisco' in self.device['device_type']:
                self.conn.save_config()
            return result
        except Exception as e:
            return f"Error executing set commands: {str(e)}"

    def disconnect(self):
        """
        Disconnect from the device.
        """
        if self.conn:
            self.conn.disconnect()