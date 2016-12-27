import random
import logging
import string
import os
import inspect
from shutit_module import ShutItModule

class shutit_nomad(ShutItModule):


	def build(self, shutit):
		vagrant_image = shutit.cfg[self.module_id]['vagrant_image']
		vagrant_provider = shutit.cfg[self.module_id]['vagrant_provider']
		gui = shutit.cfg[self.module_id]['gui']
		memory = shutit.cfg[self.module_id]['memory']
		shutit.cfg[self.module_id]['vagrant_run_dir'] = os.path.dirname(os.path.abspath(inspect.getsourcefile(lambda:0))) + '/vagrant_run'
		run_dir = shutit.cfg[self.module_id]['vagrant_run_dir']
		module_name = 'shutit_nomad_' + ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(6))
		shutit.send('command rm -rf ' + run_dir + '/' + module_name + ' && command mkdir -p ' + run_dir + '/' + module_name + ' && command cd ' + run_dir + '/' + module_name)
		if shutit.send_and_get_output('vagrant plugin list | grep landrush') == '':
			shutit.send('vagrant plugin install landrush')
		shutit.send('vagrant init ' + vagrant_image)
		shutit.send_file(run_dir + '/' + module_name + '/Vagrantfile','''Vagrant.configure("2") do |config|
  config.landrush.enabled = true
  config.vm.provider "virtualbox" do |vb|
    vb.gui = ''' + gui + '''
    vb.memory = "''' + memory + '''"
  end

  config.vm.define "nomad1" do |nomad1|
    nomad1.vm.box = ''' + '"' + vagrant_image + '"' + '''
    nomad1.vm.hostname = "nomad1.vagrant.test"
  end
  config.vm.define "nomad2" do |nomad2|
    nomad2.vm.box = ''' + '"' + vagrant_image + '"' + '''
    nomad2.vm.hostname = "nomad2.vagrant.test"
  end
  config.vm.define "nomad3" do |nomad3|
    nomad3.vm.box = ''' + '"' + vagrant_image + '"' + '''
    nomad3.vm.hostname = "nomad3.vagrant.test"
  end
end''')
		pw = shutit.get_env_pass()
		try:
			shutit.multisend('vagrant up --provider ' + shutit.cfg['shutit-library.virtualization.virtualization.virtualization']['virt_method'] + " nomad1",{'assword for':pw,'assword:':pw},timeout=99999)
		except NameError:
			shutit.multisend('vagrant up nomad1',{'assword for':pw,'assword:':pw},timeout=99999)
		if shutit.send_and_get_output("""vagrant status | grep -w ^nomad1 | awk '{print $2}'""") != 'running':
			shutit.pause_point("machine: nomad1 appears not to have come up cleanly")
		try:
			shutit.multisend('vagrant up --provider ' + shutit.cfg['shutit-library.virtualization.virtualization.virtualization']['virt_method'] + " nomad2",{'assword for':pw,'assword:':pw},timeout=99999)
		except NameError:
			shutit.multisend('vagrant up nomad2',{'assword for':pw,'assword:':pw},timeout=99999)
		if shutit.send_and_get_output("""vagrant status | grep -w ^nomad2 | awk '{print $2}'""") != 'running':
			shutit.pause_point("machine: nomad2 appears not to have come up cleanly")
		try:
			shutit.multisend('vagrant up --provider ' + shutit.cfg['shutit-library.virtualization.virtualization.virtualization']['virt_method'] + " nomad3",{'assword for':pw,'assword:':pw},timeout=99999)
		except NameError:
			shutit.multisend('vagrant up nomad3',{'assword for':pw,'assword:':pw},timeout=99999)
		if shutit.send_and_get_output("""vagrant status | grep -w ^nomad3 | awk '{print $2}'""") != 'running':
			shutit.pause_point("machine: nomad3 appears not to have come up cleanly")


		# machines is a dict of dicts containing information about each machine for you to use.
		machines = {}
		machines.update({'nomad1':{'fqdn':'nomad1.vagrant.test'}})
		ip = shutit.send_and_get_output('''vagrant landrush ls | grep -w ^''' + machines['nomad1']['fqdn'] + ''' | awk '{print $2}' ''')
		machines.get('nomad1').update({'ip':ip})
		machines.update({'nomad2':{'fqdn':'nomad2.vagrant.test'}})
		ip = shutit.send_and_get_output('''vagrant landrush ls | grep -w ^''' + machines['nomad2']['fqdn'] + ''' | awk '{print $2}' ''')
		machines.get('nomad2').update({'ip':ip})
		machines.update({'nomad3':{'fqdn':'nomad3.vagrant.test'}})
		ip = shutit.send_and_get_output('''vagrant landrush ls | grep -w ^''' + machines['nomad3']['fqdn'] + ''' | awk '{print $2}' ''')
		machines.get('nomad3').update({'ip':ip})

		for machine in sorted(machines.keys()):
			shutit.login(command='vagrant ssh ' + machine)
			shutit.login(command='sudo su -',password='vagrant')
			root_password = 'root'
			shutit.install('net-tools') # netstat needed
			if not shutit.command_available('host'):
				shutit.install('bind-utils') # host needed
			# Workaround for docker networking issues + landrush.
			shutit.send("""echo "$(host -t A index.docker.io | grep has.address | head -1 | awk '{print $NF}') index.docker.io" >> /etc/hosts""")
			shutit.send("""echo "$(host -t A registry-1.docker.io | grep has.address | head -1 | awk '{print $NF}') registry-1.docker.io" >> /etc/hosts""")
			shutit.multisend('passwd',{'assword:':root_password})
			shutit.send("""sed -i 's/.*PermitRootLogin.*/PermitRootLogin yes/g' /etc/ssh/sshd_config""")
			shutit.send("""sed -i 's/.*PasswordAuthentication.*/PasswordAuthentication yes/g' /etc/ssh/sshd_config""")
			shutit.send('service ssh restart || systemctl restart sshd')
			shutit.multisend('ssh-keygen',{'Enter':'','verwrite':'n'})
			shutit.logout()
			shutit.logout()
		for machine in sorted(machines.keys()):
			shutit.login(command='vagrant ssh ' + machine)
			shutit.login(command='sudo su -',password='vagrant')
			for copy_to_machine in machines:
				for item in ('fqdn','ip'):
					shutit.multisend('ssh-copy-id root@' + machines[copy_to_machine][item],{'assword:':root_password,'ontinue conn':'yes'})
			shutit.logout()
			shutit.logout()
		for machine in sorted(machines.keys()):
			shutit.login(command='vagrant ssh ' + machine)
			shutit.login(command='sudo su -',password='vagrant')
			# cf: https://github.com/hashicorp/nomad/commit/b561a9b835d25f86782cf878357cc6ccdb572eae
			#     https://github.com/hashicorp/nomad/pull/2122
			shutit.send('''sed -i -e "s/.*nomad.*/$(ip route get 1 | awk '{print $NF;exit}') nomad/" /etc/hosts''')
			shutit.install('unzip')
			shutit.send('wget https://releases.hashicorp.com/nomad/0.5.2/nomad_0.5.2_linux_amd64.zip')
			shutit.send('unzip nomad_0.5.2_linux_amd64.zip')
			shutit.send('mv nomad /usr/local/bin')
			shutit.send('rm -rf nomad*')
			# Set up needed directories
			shutit.send('mkdir -p /opt/nomad/{alloc,client,state}')
			shutit.logout()
			shutit.logout()
		shutit.login(command='vagrant ssh ' + sorted(machines.keys())[0])
		shutit.login(command='sudo su -',password='vagrant')
		TODO: add in client as well?
		shutit.send_file('/root/server.hcl','''# Increase log verbosity
log_level = "DEBUG"

# Setup data dir
data_dir = "/tmp/server1"

# Enable the server
server {
    enabled = true

    # Self-elect, should be 3 or 5 for production
    bootstrap_expect = 3
    retry_join = ["''' + machines['nomad1']['ip'] + ''':4648"]
}''')
		shutit.send('nohup nomad agent -config server.hcl &')
		shutit.logout()
		shutit.logout()
		
		shutit.login(command='vagrant ssh ' + sorted(machines.keys())[1])
		shutit.login(command='sudo su -',password='vagrant')
		TODO: add in server as well?
		shutit.send_file('client.hcl','''client {
  enabled = true
  servers = ["172.28.128.26:4647"]
  alloc_dir = "/opt/nomad/alloc"
  state_dir = "/opt/nomad/state"
}''')
		shutit.send('nomad agent -client -config client.hcl')
		shutit.logout()
		shutit.logout()


		# TODO: as above?
		shutit.login(command='vagrant ssh ' + sorted(machines.keys())[2])
		shutit.login(command='sudo su -',password='vagrant')
		shutit.logout()
		shutit.logout()
		shutit.log('''Vagrantfile created in: ''' + shutit.cfg[self.module_id]['vagrant_run_dir'] + '/' + module_name,add_final_message=True,level=logging.DEBUG)
		shutit.log('''Run:

	cd ''' + shutit.cfg[self.module_id]['vagrant_run_dir'] + '/' + module_name + ''' && vagrant status && vagrant landrush ls

To get a picture of what has been set up.''',add_final_message=True,level=logging.DEBUG)
		return True


	def get_config(self, shutit):
		shutit.get_config(self.module_id,'vagrant_image',default='ubuntu/trusty64')
		shutit.get_config(self.module_id,'vagrant_provider',default='virtualbox')
		shutit.get_config(self.module_id,'gui',default='false')
		shutit.get_config(self.module_id,'memory',default='1024')
		shutit.get_config(self.module_id,'vagrant_run_dir',default='/tmp')
		return True

	def test(self, shutit):
		return True

	def finalize(self, shutit):
		return True

	def is_installed(self, shutit):
		# Destroy pre-existing, leftover vagrant images.
		shutit.run_script('''#!/bin/bash
MODULE_NAME=shutit_nomad
rm -rf $( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )/vagrant_run/*
if [[ $(command -v VBoxManage) != '' ]]
then
	while true
	do
		VBoxManage list runningvms | grep ${MODULE_NAME} | awk '{print $1}' | xargs -IXXX VBoxManage controlvm 'XXX' poweroff && VBoxManage list vms | grep shutit_nomad | awk '{print $1}'  | xargs -IXXX VBoxManage unregistervm 'XXX' --delete
		# The xargs removes whitespace
		if [[ $(VBoxManage list vms | grep ${MODULE_NAME} | wc -l | xargs) -eq '0' ]]
		then
			break
		else
			ps -ef | grep virtualbox | grep ${MODULE_NAME} | awk '{print $2}' | xargs kill
			sleep 10
		fi
	done
fi
if [[ $(command -v virsh) ]] && [[ $(kvm-ok 2>&1 | command grep 'can be used') != '' ]]
then
	virsh list | grep ${MODULE_NAME} | awk '{print $1}' | xargs -n1 virsh destroy
fi
''')
		return False

	def start(self, shutit):
		return True

	def stop(self, shutit):
		return True

def module():
	return shutit_nomad(
		'imiell.shutit_nomad.shutit_nomad', 548308118.0001,
		description='',
		maintainer='',
		delivery_methods=['bash'],
		depends=['shutit.tk.setup','shutit-library.virtualization.virtualization.virtualization','tk.shutit.vagrant.vagrant.vagrant']
	)
