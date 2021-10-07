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
install -d \
    --owner=os_user \
    --group=os_group \
    --mode=700 \
    /home/gitsync/.ssh

cp id_rsa id_rsa.pub /home/gitsync/.ssh
chmod 600 /home/gitsync/.ssh/id_rsa
chmod 644 /home/gitsync/.ssh/id_rsa.pub

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