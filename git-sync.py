#!/usr/bin/python3
import os,sys,fcntl,syslog,\
	time,subprocess,yaml,optparse

program_opt={
	'log_level'         : 10,
	'git_verbose_level' : 5,
	'verbose'           : 1,
	'show_help'         : 0,
	'spool_base'        : "/opt/git-sync",
	'config_file'       : "/home/git-sync/git-sync.yaml",
	'git_site'          : 'git@github.com:spaolo/git-sync.git',
	'git_user_home'     : '/home/git-sync/',
	'repo_spool'        : 'git-sync'
}

with open(program_opt['config_file'], 'r') as stream:
    try:
        config_file_opt=yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)
    stream.close()

#merge config on default
for keyword in program_opt.keys():
	if keyword in config_file_opt.keys():
		program_opt[keyword]=config_file_opt[keyword]

#program_opt['dry_run']=0
#program_opt['trigger_reload']=0

myself=os.path.basename(sys.argv[0])
syslog.openlog(myself,syslog.LOG_PID,syslog.LOG_DAEMON)

# spool_dir="/opt/git-sync"
# git_site='git@github.com:spaolo/git-sync.git'
# git_user_home='/home/git-sync/'

git_root=program_opt['spool_base'] + '/' +program_opt['repo_spool']

# GetOptions(
# 	"verbose|v" => \$verbose,
# 	"debug|d"   => \$debug,
# 	"base|b"    => \$program_opt['spool_base'],
# 	"help|h"    => \$help
# )

if program_opt['show_help']:
	print(sys.argv[0]+" usage")
	print("      -v|--verbose  show more detail")
	print("      -d|--debug    show relevant steps")
	print("      -b|--base     use a different basedir (" + program_opt[''] +")")
	print("      -h|--help     shows help")
	sys.exit(0)

# #load config file
# if ( -f $program_opt[''].'/etc/git-sync.cfg' ) {
# 	do $program_opt[''].'/etc/git-sync.cfg'
# }

git_cmd='git'

git_quiet_flag=''
if program_opt['log_level'] < program_opt['git_verbose_level']:
	git_quiet_flag=' --quiet '

git_ssh_helper=program_opt['git_user_home']+'/git_ssh'
git_user_key=program_opt['git_user_home']+'/.ssh/id_rsa'
git_config_file=program_opt['git_user_home']+'/.gitconfig'
git_revision='master'
git_remote='origin'
state_dir=program_opt['spool_base']+'/state'

os.environ["GIT_SSH"]=git_ssh_helper
os.environ["HOME"]=program_opt['git_user_home']

#set home for git
#export HOME=/home/automata
#git_ssh_helper=$HOME/git_ssh
#export GIT_SSH=$git_ssh_helper

#######################################################################################################
#{log libs
#######################################################################################################
def log_message(level,message,too=''):
  ''' logging utility  '''
  if level < program_opt['log_level']:
    syslog.syslog(myself+': '+message)
    if program_opt['verbose'] > 0:
      print (message+' '+too) 

def log_and_die(error_message):
  log_message(0,error_message)
  sys.exit(256)

#######################################################################################################
#}log libs
#######################################################################################################
#######################################################################################################
#{git libs
#######################################################################################################
def git_clone(git_root,git_site):
	sys_rc=os.system(git_cmd + ' clone ' + git_quiet_flag + git_site + ' ' + git_root)
	#os.waitstatus_to_exitcode
	if (sys_rc>>8) == 1:
		log_and_die("git clone " + git_site+ " "+ git_root)
	else:
		log_message(5,"git clone " + git_site + " "+ git_root + " ok")
	

def git_revparse(git_root,git_branch):
	#branch_ref=`$git_cmd rev-parse $git_quiet_flag $git_branch`
	#FIXME add a proper way to handle git_quiet_flag
	branch_ref = 'none'
	if program_opt['log_level'] < program_opt['git_verbose_level']:
		branch_ref = subprocess.check_output([git_cmd, 'rev-parse', '--quiet', git_branch ])
	else:
		branch_ref = subprocess.check_output([git_cmd, 'rev-parse', git_branch ])
	#FIXME
	# if os.waitstatus_to_exitcode(sys_rc) == 1:
	# 	log_and_die("git rev-parse " + git_branch + " failed")
	# else:
	# 	log_message(5,"git rev-parse "+ git_branch+ " returned "+ branch_ref)

	return branch_ref

def git_add_file(git_root,add_file,author_string,commit_message):

	sys_rc=os.system(git_cmd + ' add ' + add_file)

	if (sys_rc>>8) == 1:
		log_and_die("git add " + add_file + " failed")
	else:
		log_message(5,"git add "+ add_file+" ok")

	sys_rc=os.system( git_cmd + ' commit ' + git_quiet_flag + ' --author "' + author_string + '" -m "' + commit_message + '"')
	if (sys_rc>>8) == 1:
		log_and_die("git commit " + add_file + " failed")
	else:
		log_message(5,"git commit " + add_file + "ok")

def git_push(git_root):
	os.chdir(git_root)
	sys_rc=os.system( git_cmd + ' push' + git_quiet_flag)
	if (sys_rc>>8) == 1:
		log_and_die("git push failed")
	else:
		log_message(5,"git push ok")

def git_fetch_spool(git_root,git_remote,git_branch):
	sys_rc=os.system( git_cmd + ' fetch' + git_quiet_flag)
	if (sys_rc>>8) == 1:
		log_and_die("git fetch " + git_root + " failed")
	else:
		log_message(5,"git fetch " + git_root +" ok")
	#set changed not synked for return
	changed = 1 if git_check_sync(git_root,git_remote,git_branch) == 1 else 0
	sys_rc=os.system(git_cmd + ' reset ' + git_quiet_flag + '--hard ' + git_remote + '/' + git_branch)
	if (sys_rc>>8) == 1:
		log_and_die("git reset " + git_root + "failed")
	else:
		log_message(5,"git reset " + git_root +"ok")
	return changed

def git_prep_spool(git_root,git_site,git_remote,git_revision):
	os.chdir(program_opt['spool_base'])
	changed=0
	if os.path.isdir(git_root+'/.git'):
		os.chdir(git_root)
		#spool is present fetch and update
		changed=git_fetch_spool(git_root,git_remote,git_revision)
		if git_check_sync(git_root,git_remote,git_revision) == 0 :
			log_message(5,"git spool out of sync rebuild")
			os.rename(git_root, git_root+'.'+ str(time.time()))
			os.makedirs(git_root, exist_ok=True)
			os.chdir(git_root)
			git_clone(git_root,git_site)
			return 1
		return changed
	else:
		git_clone(git_root,git_site)
		changed=git_fetch_spool(git_root,git_remote,git_revision)
		return 1


def git_check_sync(git_root,git_remote,git_revision):
	os.chdir(git_root)
	local_commit=git_revparse(git_root,git_revision)
	remote_commit=git_revparse(git_root,git_remote + '/' + git_revision)

	if ( local_commit == remote_commit ):
		return 1
	else:
		return 0

def git_check_branch(git_root,git_revision):
	os.chdir(git_root)
	current_branch=git_revparse(+git_root,'--abbrev-ref HEAD')
	if git_revision == current_branch:
		return 1
	else:
		return 0


#######################################################################################################
#}git libs
#######################################################################################################

#######################################################################################################
#{defs and utils
#######################################################################################################

def time_daystring(to_cnv):
	now_string=time.strftime("%Y%m%d%H%M%S", to_cnv)
	return now_string
#
#######################################################################################################
#}defs and utils
#######################################################################################################
#######################################################################################################
#######################################################################################################

lock_name='/tmp/'+myself+'.lock'
#avoid multiple concurrent run
lock_fh=open(lock_name,'a+')
try:
  fcntl.flock(lock_fh.fileno(),fcntl.LOCK_EX | fcntl.LOCK_NB)
except IOError:
  log_message(0,' aborting other istance running' )
  sys.exit(2)

log_message(0,'sync start')
#daystring=time_daystring(time)

log_message(0,'pull git')
print(git_root)
changed=git_prep_spool(git_root,program_opt['git_site'],git_remote,git_revision)
log_message(0,'sync complete')

fcntl.flock(lock_fh.fileno(),fcntl.LOCK_UN);
lock_fh.close()
os.remove(lock_name)

sys.exit(changed)
