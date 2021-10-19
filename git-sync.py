#!/usr/bin/python3
import os,sys,fcntl,syslog,\
        time,subprocess,yaml,optparse, \
        shutil,filecmp
#######################################################################################################
#{default config 
#######################################################################################################

program_opt={
        'log_level'         : 10,
        'git_verbose_level' : 5,
        'verbose'           : False,
        'show_help'         : 0,
        'spool_base'        : "/opt/git-sync",
        'config_file'       : "/home/git-sync/git-sync.yaml",
        'git_site'          : 'git@github.com:spaolo/git-sync.git',
        'git_cmd'           : 'git',
        'git_branch'        : 'master',
        'git_user_home'     : '/home/git-sync/',
        'git_author_name'   : 'Author Name',
        'git_author_mail'   : 'author@example.com',
        'git_commit_prefix' : 'commited at',
        'repo_spool'        : 'git-sync'
}
optional_config_keys=[ 'push_map' ]
#######################################################################################################
#}default config 
#######################################################################################################
#######################################################################################################
#{config first stage
#######################################################################################################
opt_obj = optparse.OptionParser()
opt_obj.add_option("-c", "--config",
                  dest="config_file",
                  default=program_opt['config_file'],
                  help="write report to FILE",
                  metavar="FILE")

opt_obj.add_option("-v", "--verbose",
                  action="store_true",
                  dest="verbose",
                  default=False,
                  help="don't print status messages to stdout")

#override default configs
(cli_opt, args) = opt_obj.parse_args()
with open(cli_opt.config_file, 'r') as stream:
    try:
        config_file_opt=yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)
    stream.close()

#merge config on default
for keyword in program_opt.keys():
        if keyword in config_file_opt.keys():
                program_opt[keyword]=config_file_opt[keyword]

#load optional confs
for keyword in optional_config_keys:
        if keyword in config_file_opt.keys():
                program_opt[keyword]=config_file_opt[keyword]

#override verbosity
if cli_opt.verbose:
    program_opt['verbose']=True

#######################################################################################################
#}config first stage
#######################################################################################################
#######################################################################################################
#{config second stage
#######################################################################################################
myself=os.path.basename(sys.argv[0])
myself=os.path.basename(sys.argv[0])
syslog.openlog(myself,syslog.LOG_PID,syslog.LOG_DAEMON)

git_root=program_opt['spool_base'] + '/' +program_opt['repo_spool']

git_cmd=program_opt['git_cmd']
git_quiet_flag=''
if program_opt['log_level'] < program_opt['git_verbose_level']:
        git_quiet_flag=' --quiet '

git_ssh_helper=program_opt['git_user_home']+'/git_ssh'
git_user_key=program_opt['git_user_home']+'/.ssh/id_rsa'
git_config_file=program_opt['git_user_home']+'/.gitconfig'
#git_branch='master'
git_remote='origin'
state_dir=program_opt['spool_base']+'/state'

os.environ["GIT_SSH"]=git_ssh_helper
os.environ["HOME"]=program_opt['git_user_home']
#######################################################################################################
#}config second stage
#######################################################################################################

#######################################################################################################
#{log libs
#######################################################################################################
def log_message(level,message,too=''):
  ''' logging utility  '''
  if level < program_opt['log_level']:
    syslog.syslog(myself+': '+message)
    if program_opt['verbose']:
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
def git_suppress_out(command_line):
        '''
        Append shell null redirection for commands
        '''
        if program_opt['log_level'] < program_opt['git_verbose_level']:
                return command_line+' >> /dev/null 2>&1'
        else:
                return command_line

def git_clone(git_root,git_site):
        '''
        git clone wrapper
        '''
        git_clone_cmd=git_suppress_out(git_cmd + ' clone ' + git_quiet_flag + git_site + ' ' + git_root)
        sys_rc=os.system(git_clone_cmd)
        #os.waitstatus_to_exitcode
        if (sys_rc>>8) == 1:
                log_and_die("git clone " + git_site+ " "+ git_root)
        else:
                log_message(5,"git clone " + git_site + " "+ git_root + " ok")
        

def git_revparse(git_root,git_branch):
        '''
        git revparse wrapper get the actual local repo position
        '''
        os.chdir(git_root)
        #FIXME add a proper way to handle git_quiet_flag
        return_val = 'none'
        if program_opt['log_level'] < program_opt['git_verbose_level']:
                branch_ref = subprocess.check_output([git_cmd, 'rev-parse', '--quiet', git_branch ])
        else:
                branch_ref = subprocess.check_output([git_cmd, 'rev-parse', git_branch ])

        return_val=branch_ref.decode("utf-8").rstrip()
        #FIXME
        # handle error on output basis
        # if os.waitstatus_to_exitcode(sys_rc) == 1:
        #         log_and_die("git rev-parse " + git_branch + " failed")
        # else:
        #         log_message(5,"git rev-parse "+ git_branch+ " returned "+ branch_ref)

        return return_val

def git_add_file(git_root,add_file):
        '''
        Git ad a file no commit or push
        '''
        os.chdir(git_root)
        
        git_add_cmd=git_suppress_out(git_cmd + ' add ' + add_file)
        sys_rc=os.system(git_add_cmd)
        if (sys_rc>>8) == 1:
                log_and_die("git add " + add_file + " failed")
        else:
                log_message(5,"git add "+ add_file+" ok")

def git_commit(git_root,author_string,commit_message):
        '''
        Git commit wrapper
        '''
        os.chdir(git_root)
        git_commit_cmd=git_suppress_out(git_cmd + ' commit ' + git_quiet_flag + ' --author "' + author_string + '" -m "' + commit_message + '"')
        sys_rc=os.system( git_commit_cmd )

        if (sys_rc>>8) == 1:
               log_and_die("git commit failed")
        else:
               log_message(5,"git commit ok")

def git_push(git_root):
        '''
        Git pull wrapper
        '''
        os.chdir(git_root)
        git_push_cmd=git_suppress_out(git_cmd + ' push' + git_quiet_flag)
        sys_rc=os.system( git_push_cmd )

        if (sys_rc>>8) == 1:
                log_and_die("git push failed")
        else:
                log_message(5,"git push ok")


def git_fetch_spool(git_root,git_remote,git_branch):
        '''
        Sync an existing local repo dir
        '''
        os.chdir(git_root)
        git_fetch_cmd=git_suppress_out(git_cmd + ' fetch' + git_quiet_flag)
        sys_rc=os.system( git_fetch_cmd)
        if (sys_rc>>8) == 1:
                log_and_die("git fetch " + git_root + " failed")
        else:
                log_message(5,"git fetch " + git_root +" ok")
        #change branch if needed
        if not git_check_branch(git_root,git_branch):
                git_checkout_cmd=git_suppress_out(git_cmd+' checkout '+git_quiet_flag+git_branch)
                sys_rc=os.system(git_checkout_cmd)
                if (sys_rc>>8) == 1:
                        log_and_die("git checkout %s %s failed" % (git_root,git_branch) )
                else:
                        log_message(5,"git checkout %s ok" % git_root)

        #set changed not synked for return
        git_reset_cmd=git_suppress_out(git_cmd+' reset '+git_quiet_flag+'--hard '+git_remote+'/'+git_branch)
        sys_rc=os.system(git_reset_cmd)

        if (sys_rc>>8) == 1:
                log_and_die("git reset " + git_root + " failed")
        else:
                log_message(5,"git reset " + git_root +" ok")

def git_prep_spool(git_root,git_site,git_remote,git_branch):
        '''
        Prepare spool directory with the latest up to date version
        '''
        os.chdir(program_opt['spool_base'])
        changed=False
        if os.path.isdir(git_root+'/.git'):
                os.chdir(git_root)
                #spool is present fetch and update
                git_fetch_spool(git_root,git_remote,git_branch)
                if not git_check_sync(git_root,git_remote,git_branch):
                        log_message(5,"git spool out of sync rebuild")
                        os.rename(git_root, git_root+'.'+ str(time.time()))
                        os.makedirs(git_root, exist_ok=True)
                        os.chdir(git_root)
                        git_clone(git_root,git_site)
                        changed=True
        else:
                git_clone(git_root,git_site)
                changed=git_fetch_spool(git_root,git_remote,git_branch)
                changed=True
        return changed


def git_check_sync(git_root,git_remote,git_branch):
        '''
        Check if local repo requires fetch+pull
        '''
        os.chdir(git_root)
        local_commit=git_revparse(git_root,git_branch)
        remote_commit=git_revparse(git_root,git_remote + '/' + git_branch)
        log_message(15,"local_commit %s remote_commit %s" %( local_commit, remote_commit)) 

        if ( local_commit == remote_commit ):
                return True
        else:
                return False

def git_check_branch(git_root,git_branch):
        '''
        Check if current position match revision
        '''
        os.chdir(git_root)
        current_branch=git_revparse(git_root,'--abbrev-ref HEAD')
        if git_branch == current_branch:
                return True
        else:
                return False

#######################################################################################################
#}git libs
#######################################################################################################
#######################################################################################################
#{defs and utils
#######################################################################################################

def time_daystring(to_cnv):
    '''
    Format daystring  for commit
    '''
    now_string=to_cnv.strftime("%Y%m%d%H%M%S")
    return now_string
#
#######################################################################################################
#}defs and utils
#######################################################################################################
#######################################################################################################
#{sync libs
#######################################################################################################
def need_update(src_path,dst_path):
    '''
    Check if a mapped file will require copy and update
    '''
    if not os.path.isfile(dst_path):
        log_message(2,"need_update: %s new file" % dst_path)
        return True
    elif filecmp.cmp(src_path,dst_path):
        log_message(2,"need_update: %s up to date" % dst_path)
        return False
    else:
        log_message(2,"need_update: %s changed" % dst_path)
        return True
   
def add_element(push_base,dest_prefix,push_element):
    '''
    push a single leaf of a tree
    '''
    dirname=os.path.dirname(push_element)

    src_path=os.path.join(push_base,push_element)
    src_dirname=os.path.join(push_base,dirname)
    dst_path=os.path.join(git_root,dest_prefix+push_element)
    dst_dirname=os.path.join(git_root,dest_prefix+dirname)

    return_changed=False
    if os.path.isfile(src_path):
        #create remote remote basendir
        os.makedirs(dst_dirname, exist_ok=True)
        #check if differs
        if need_update(src_path,dst_path):
            #copy file
            shutil.copyfile(src_path,dst_path)
            #add to git
            git_add_file(git_root,dest_prefix+push_element)
            return_changed=True

    elif os.path.isdir(src_path):
        os.makedirs(dst_path, exist_ok=True)
        #consider all files
        for src_f in os.listdir(src_path):
            #shorthand for source and dest
            src_subpath=os.path.join(src_path,src_f)
            dst_subpath=os.path.join(dst_path,src_f)
            if os.path.isfile(src_subpath) and need_update(src_subpath,dst_subpath):
                shutil.copyfile(src_subpath,dst_subpath)
                git_add_file(git_root,os.path.join(dest_prefix+push_element,src_f))
                return_changed=True
    else:
        log_message(0,"original file %s missing" % src_path)
    return return_changed

def push_schema(schema_name,schema_to_push):
    '''
    push a single tree
    '''
    if 'push_dir' not in schema_to_push.keys():
        log_message(2,"schema %s no push_dir defined" % schema_name)
        return
    dest_prefix=''
    if 'prepend_dir_basename' in schema_to_push.keys() and schema_to_push['prepend_dir_basename']:
        dest_prefix=os.path.basename(schema_to_push['push_dir'])+'/'

    log_message(2,"schema %s pushing dir %s" % (schema_name,schema_to_push['push_dir']) )

    return_changed=False
    if 'push_files' not in schema_to_push.keys():
        log_message(2,"schema %s no push_files to push" % schema_name)
    else:
        for push_elem in schema_to_push['push_files']:
            log_message(2,"schema %s add element %s" % (schema_name,dest_prefix+push_elem) )
            if add_element(schema_to_push['push_dir'],dest_prefix,push_elem):
                return_changed=True
    #final return
    return return_changed

def push_phase():
    '''
    list push_map and pass it to single tree schema pusher
    '''
    if 'push_map' not in program_opt.keys():
        log_message(2,"push_phase: push_map nor defined")
        return
    return_changed=False
    for schema_name in program_opt['push_map'].keys():
        if push_schema(schema_name,program_opt['push_map'][schema_name]):
            return_changed=True

    if return_changed:
        author_string="'%s' <%s>" % (program_opt['git_author_name'],program_opt['git_author_mail'])
        commit_message="%s %s" % (program_opt['git_commit_prefix'],time_daystring(time))
        git_commit(git_root, author_string, commit_message)
        git_push(git_root)


#######################################################################################################
#}sync libs
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

log_message(0,'git pull...')
changed=git_prep_spool(git_root,program_opt['git_site'],git_remote,program_opt['git_branch'])
log_message(0,'pull complete')
log_message(0,'git add commit push...')
push_phase()
log_message(0,'push complete')


fcntl.flock(lock_fh.fileno(),fcntl.LOCK_UN);
lock_fh.close()
os.remove(lock_name)

sys.exit(changed)
