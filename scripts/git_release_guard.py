"""A deployment must correspond to a clean commit already present on origin."""

import subprocess


def published_revision(repo):
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=repo, text=True).strip()
    if git('status', '--porcelain'):
        raise SystemExit('Commit and push all changes before deployment')
    revision = git('rev-parse', 'HEAD')
    branch = git('branch', '--show-current')
    if not branch:
        raise SystemExit('Deployment requires a named published branch')
    remote = git('ls-remote', '--heads', 'origin', 'refs/heads/' + branch)
    if not remote or remote.split()[0] != revision:
        raise SystemExit('HEAD differs from the GitHub branch: push before deployment')
    return revision
