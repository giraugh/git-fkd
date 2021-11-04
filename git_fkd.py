from pathlib import Path
from sh.contrib import git
import os


def find_repos(cwd=u'.'):
    """ Find dirty repos """
    repos = []
    top = Path(cwd).expanduser().resolve()
    for root, dirs, _ in os.walk(top):
        if '.git' in dirs:
            repos.append(os.path.abspath(root))
    return repos


def get_branch_status(repo_path, branch, remote_branch):
    # Compare revs
    behind = git('rev-list', '--count', f'{branch}..{remote_branch}', '--', _cwd=repo_path)
    ahead = git('rev-list', '--count', f'{remote_branch}..{branch}', '--', _cwd=repo_path)
    behind, ahead = int(behind), int(ahead)

    # Determine status
    status = ''
    if behind == ahead == 0:
        status = 'up to date'
    elif behind == 0 and ahead > 0:
        status = 'ahead'
    elif ahead == 0 and behind > 0:
        status = 'behind'
    else:
        status = 'diverged'

    return status


def repo_branch_statuses(repo_path):
    # First fetch up to date info
    git.fetch('--all', _cwd=repo_path)

    # Get branch pairs
    statuses = []
    branch_pairs = get_branch_pairs(repo_path)
    for branch, remote_branch in branch_pairs:
        status = get_branch_status(repo_path, branch, remote_branch)
        if status != 'up to date':
            statuses.append((branch, status))

    return statuses


def get_branch_pairs(repo_path):
    # Get all branches, remote branches and remotes
    branch_output = git.branch('-a', '--no-color', _cwd=repo_path)
    branches = [b.strip() for b in branch_output.split('\n')]

    # Tidy branch formatting
    for i, b in enumerate(branches):
        if b[:2] == '* ':
            branches[i] = b[2:]
        if '->' in b or len(b) == 0:
            branches.remove(b)

    # Get all remotes
    remotes = git.remote(_cwd=repo_path).split('\n')

    # Find branches that have associated remote branches
    branch_pairs = []
    local_branches = [b for b in branches if 'remotes/' not in b]
    for b in local_branches:
        remote_branch = next(
            (f'{r}/{b}' for r in remotes if f'remotes/{r}/{b}' in branches), None)
        if not remote_branch:
            continue
        else:
            branch_pairs.append((b, remote_branch))

    return branch_pairs


def repo_is_dirty(repo_path):
    st = git.status('--porcelain', _cwd=repo_path)
    return len(st) > 0


def find_dirty(cwd=u'.'):
    return filter(repo_is_dirty, find_repos(cwd))


def analyse_repo(repo_path):
    stats = {}
    st = git.status('--porcelain', _cwd=repo_path)
    st_lines = [x for x in st.split('\n') if len(x) > 0]
    stats['modified'] = len([n for n in st_lines if n.strip()[0] == 'M'])
    stats['untracked'] = len([n for n in st_lines if n.strip()[:2] == '??'])
    return stats


if __name__ == '__main__':
    # Find ahead
    for r in find_repos('~/r'):
        statuses = repo_branch_statuses(r)
        out_of_sync = len(statuses) > 0
        dirty = repo_is_dirty(r)

        if out_of_sync or dirty:
            print(f'[{os.path.basename(r)}]')

        if dirty:
            st = analyse_repo(r)
            print('dirty:')
            if st["modified"] > 0:
                print(f'\t{st["modified"]} modified')
            if st["untracked"] > 0:
                print(f'\t{st["untracked"]} untracked')

        if out_of_sync:
            print('out of sync:')
        for branch, status in statuses:
            print(f'\t{branch} is {status}')

        if out_of_sync or dirty:
            print('')
