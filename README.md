# git-sync
push or pull a directory to a git repo

# install
mkdir /home/git-sync /opt/git-sync
chown -R os_user /home/git-sync/ /opt/git-sync

install -d \
    --owner=os_user \
    --group=os_group \
    --mode=755 \
    /home/git-sync/ /opt/git-sync

```
install \
    --owner=os_user \
    --group=os_group \
    --mode=755 \
    git_ssh /home/git-sync/git_ssh
```

## ssh-key access
```
install -d \
    --owner=os_user \
    --group=os_group \
    --mode=700 \
    /home/gitsync/.ssh

cp id_rsa id_rsa.pub /home/gitsync/.ssh
chmod 600 /home/gitsync/.ssh/id_rsa
chmod 644 /home/gitsync/.ssh/id_rsa.pub
```

## user, password or token access

### dirty way
configure with user and password sintax in the git_site url config

es 'https://user:pasguord@github.com:spaolo/git-sync.git'

### better way
configure credential store

configure credential helper for git config
```
git config \
    --file /home/git-sync/.gitconfig \
    credential.helper  \
    'store --file /home/git-sync/.git-credentials'
```

prepare a credential snippet like this one in a text editor

```
protocol=https
host=github.com
username=bob
password=s3cre7
```

now feed the snippet to the credential store 

```
git credential-store \
    --file /home/git-sync/.git-credentials \
    store
```

Resoulting config should be similar the following one

$ cat /home/git-sync/.gitconfig
```
[credential]
        helper = store --file /home/git-sync/.git-credentials
```

$ ls -las /home/git-sync/.git-credentials
4 -rw------- 1 os_user os_group 30 Oct  7 13:11 /home/git-sync/.git-credentials

$ cat /home/git-sync/.git-credentials
```
https://bob:s3cre7@github.com
```

# Configure
Default config file is placed into /home/git-sync/git-sync.yaml, you can change
it by specifying -c / --config command line flag, Configuration file format is
yaml, below a sample for fetch only.

/home/git-sync/git-sync.yaml
```
---
log_level: 2
git_verbose_level: 5
repo_spool: git-sync
git_site: git@github.com:spaolo/git-sync.git
git_user_home: /home/git-sync/
```

pushing feature can be enabled by specifying push_map keyword filled with the
push schema you want to be applied, schema map is a "complex" dictionary with 
nested istances each one having a push_dir keyword to fill with path the push 
will start from and to push and push_files list with relative paths you want
to push, in case a directory is listed here all files in the directory will
be pushed, the optional prepend_dir_basename flag is available in case the
push_dir basename is needed as prefix for destination file to push

The git_author_name, git_author_mail keyword will also be needed to have the
push feature work properly.

TODO: recursive flag

Sample below

```
git_author_name: 'Author Name'
git_author_mail: 'author@example.com'
git_commit_prefix: 'automatically commited at'

push_map:
  one_dir:
    push_dir: /some/dir/
    push_files:
      - single/file/to/push
      - push/entire/directory.d
  other_dir:
    push_dir: /some/other/path/
    prepend_dir_basename: True
    push_files:
      - single/file/to/push
```

