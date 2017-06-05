import os
from collections import OrderedDict

import requests


GITLAB_URL = os.environ['GITLAB_URL']
GITLAB_TOKEN = os.environ['GITLAB_TOKEN']
GITLAB_PROJECTS = set(os.environ['GITLAB_PROJECTS'].split(','))
SLACK_URL = os.environ['SLACK_URL']


def main():
    # TODO: pagination
    projects = requests.get(
        f'{GITLAB_URL}/api/v4/projects',
        params={
            'per_page': 100,
            'simple': True,
            'order_by': 'last_activity_at'
        },
        headers={'PRIVATE-TOKEN': GITLAB_TOKEN}
    ).json()
    projects = [p for p in projects
                if p['path_with_namespace'] in GITLAB_PROJECTS]

    unresolved = OrderedDict()
    for project in projects:
        mrs = requests.get(
            f'{GITLAB_URL}/api/v4/projects/{project["id"]}/merge_requests',
            params={
                'per_page': 100,
                'state': 'opened',
                'order_by': 'created_at'
            },
            headers={'PRIVATE-TOKEN': GITLAB_TOKEN}
        ).json()
        mrs = [mr for mr in mrs if not mr['title'].startswith('WIP')]

        sublist = []
        for mr in mrs:
            if mr.get("assignee"):
                assignee = '@' + mr['assignee']['username']
            else:
                assignee = 'Unassigned'
            sublist.append(f'{assignee}: {mr["title"]}')

        unresolved[project['name_with_namespace']] = sublist

    messages = []
    for project_name, sublist in unresolved.items():
        if sublist:
            sublist = ''.join([f'- {l}\n' for l in sublist])
            messages.append(f'{project_name}\n```\n{sublist}```')

    if not messages:
        return

    message = 'There are unmerged MRs!\n\n' + '\n\n'.join(messages)
    requests.post(SLACK_URL, json={'text': message})


if __name__ == '__main__':
    main()