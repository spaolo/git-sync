#!/usr/bin/perl
use strict;
use locale;
use Sys::Syslog;
use utf8;
use POSIX qw(strftime);
use Data::Dumper;
use Sys::Hostname;
use File::Basename;
use Fcntl ':flock';
use Getopt::Long;
use LWP::UserAgent ();

my $verbose=0;
my $log_level=1;
my $debug=0;
my $dry_run=0;
my $myself=$0;
my $trigger_reload=0;
my $help=0;

$myself=basename $myself; $myself=~s/\.pl$//;

our $spool_dir="/opt/git-sync";
our $git_site='git@github.com:spaolo/git-sync.git';
our $git_user_home='/home/git-sync/';
our $git_root=$spool_dir.'/git-sync';

GetOptions(
	"verbose|v" => \$verbose,
	"debug|d"   => \$debug,
	"base|b"    => \$spool_dir,
	"dry-run|n" => \$dry_run,
	"help|h"    => \$help
);
if ($help) {
	print $0." usage\n";
	print "      -v|--verbose  show more detail\n";
	print "      -d|--debug    show relevant steps\n";
	print "      -b|--base     use a different basedir (".$spool_dir.")\n";
	print "      -n|--dry-run  mimic only, skip witing infoblox\n";
	print "      -h|--help     shows help\n";
	exit;
}

my $start_time=time();

#load config file
if ( -f $spool_dir.'/etc/git-sync.cfg' ) {
    do $spool_dir.'/etc/git-sync.cfg';
}
my $git_cmd='git';
my $git_quiet_flag='';
$git_quiet_flag=' --quiet ' unless ($debug);
my $git_ssh_helper=$git_user_home.'/git_ssh';
my $git_user_key=$git_user_home.'/.ssh/id_rsa';
my $git_config_file=$git_user_home.'/.git_config';
my $git_revision='master';
my $git_remote='origin';
my $state_dir=$spool_dir."/state";

$ENV{'GIT_SSH'}=$git_ssh_helper;
$ENV{'HOME'}=$git_user_home;

#set home for git
#export HOME=/home/automata
#git_ssh_helper=$HOME/git_ssh
#export GIT_SSH=$git_ssh_helper

#######################################################################################################
#{log libs
#######################################################################################################
sub log_to_sys(@) {
  my $verblev=shift; 
  my $mesage=join(' ',@_);
  #check debug level
  if ($verblev <= $log_level) {
    syslog('info',"%s",$mesage);
  }
}

sub log_and_die(@) {
  my $mesage=join(' ',@_);
  log_to_sys(0,$mesage);
  exit 256;
}

#######################################################################################################
#}log libs
#######################################################################################################
#######################################################################################################
#{git libs
#######################################################################################################
sub git_clone($$){
my $git_root=shift;
my $git_site=shift;
system($git_cmd.' clone '.$git_quiet_flag.$git_site.' '.$git_root);
if (($?>>8) == 1)
	{ die "git clone $git_site $git_root\n";}
else
	{ print "git clone $git_site $git_root ok\n" if ($debug); }
}

sub git_revparse($$){
my $git_root=shift;
my $git_branch=shift;
my $branch_ref=`$git_cmd rev-parse $git_quiet_flag $git_branch`;
if (($?>>8) == 1)
	{ die "git rev-parse $git_branch failed\n";}
else
	{ print "git rev-parse $git_branch returned $branch_ref\n" if ($debug); }

return $branch_ref;
}

sub git_add_file($$$$) {
	my $git_root=shift;
	my $add_file=shift;
	my $author_string=shift;
	my $commit_message=shift;

	system($git_cmd.' add '.$add_file);
	if (($?>>8) == 1)
		{ die "git add ".$add_file." failed\n";}
	else
		{ print "git add $add_file ok\n" if ($debug); }
	system($git_cmd.' commit '.$git_quiet_flag.'--author "'.$author_string.'" -m "'.$commit_message.'"');
	if (($?>>8) == 1)
		{ die "git commit ".$add_file." failed\n";}
	else
		{ print "git commit $add_file ok\n" if ($debug); }
}

sub git_push($) {
	my $git_root=shift;
	chdir $git_root;
	system($git_cmd.' push'.$git_quiet_flag);
	if (($?>>8) == 1)
		{ die "git push failed\n";}
	else
		{ print "git push ok\n" if ($debug); }
}

sub git_fetch_spool($$$){
	my $git_root=shift;
	my $git_remote=shift;
	my $git_branch=shift;
	chdir $git_root;
	system($git_cmd.' fetch'.$git_quiet_flag);
	if (($?>>8) == 1)
		{ die "git fetch $git_root failed\n"; }
	else	{ print "git fetch $git_root ok\n" if ($debug); }
	#set changed not synked for return
	my $changed = (git_check_sync($git_root,$git_remote,$git_branch) == 1 ? 0 : 1);
	system($git_cmd.' reset '.$git_quiet_flag.'--hard '.$git_remote.'/'.$git_branch);
	if (($?>>8) == 1)
		{ die "git reset $git_root failed\n"; }
	else	{ print "git reset $git_root ok\n" if ($debug); }
	return $changed;
}

sub git_prep_spool($$$$){
	my $git_root=shift;
	my $git_site=shift;
	my $git_remote=shift;
	my $git_revision=shift;
	chdir $spool_dir;
	my $changed=0;
	if ( -d $git_root.'/.git' ){
		chdir $git_root;
		#spool is present fetch and update
		$changed=git_fetch_spool($git_root,$git_remote,$git_revision);
		if ( git_check_sync($git_root,$git_remote,$git_revision) == 0 ) {
			print "git spool out of sync rebuild" if ($debug);
			rename $git_root, $git_root.'.'.time();
			`mkdir -p $git_root`;
			chdir $git_root;
			git_clone($git_root,$git_site);
			return 1;
		}
		return $changed;
	}
	else {
		git_clone($git_root,$git_site);
		$changed=git_fetch_spool($git_root,$git_remote,$git_revision);
		return 1;
	}
}

sub git_check_sync($$$){
	my $git_root=shift;
	my $git_remote=shift;
	my $git_revision=shift;
	chdir $git_root;
	my $local_commit=git_revparse($git_root,$git_revision);
	my $remote_commit=git_revparse($git_root,$git_remote.'/'.$git_revision);

	if ( $local_commit eq $remote_commit )
		{ return 1 }
	else	{ return 0 }
}

sub git_check_branch($$){
	my $git_root=shift;
	my $git_revision=shift;
	chdir $git_root;
	my $current_branch=git_revparse($git_root,'--abbrev-ref HEAD');
	if ( $git_revision eq $current_branch )
		{ return 1 }
	else 	{ return 0 }
}

#######################################################################################################
#}git libs
#######################################################################################################

#######################################################################################################
#{subs and utils
#######################################################################################################

sub time_daystring($) {
	my $to_cnv=shift;
	my $now_string = strftime '%Y%m%d%H%M%S',localtime($to_cnv);
	return $now_string;
}

#
#######################################################################################################
#}subs and utils
#######################################################################################################
#######################################################################################################
#######################################################################################################

openlog($myself,'pid','daemon')||die "failed to open syslog\n";

my $flock_file='/tmp/'.$myself.'.flock';
open (LCKRUN,"+>>$flock_file")||log_and_die ("error opening file $flock_file :$!");
my $rc=flock(LCKRUN,LOCK_EX | LOCK_NB);
sysseek (LCKRUN,0,0);
truncate LCKRUN,0;
if ($rc == 1)
	{ syswrite LCKRUN,"$$\n",length("$$\n"); }
else
	{close LCKRUN;log_and_die ("another instance is running");}

log_to_sys(0,'sync start');
my $daystring=time_daystring(time);

log_to_sys(0,'pull git');
my $changed=git_prep_spool($git_root,$git_site,$git_remote,$git_revision);
log_to_sys(0,'sync complete');
exit $changed;
