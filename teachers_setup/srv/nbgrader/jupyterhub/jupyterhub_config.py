c = get_config()

import os, nativeauthenticator
c.JupyterHub.authenticator_class = 'native'
c.JupyterHub.template_paths = [f"{os.path.dirname(nativeauthenticator.__file__)}/templates/"]
c.Authenticator.admin_users = {'tele'}
c.NativeAuthenticator.open_signup = False
c.ServerApp.allow_origin = '*'

# Our user list
c.Authenticator.allowed_users = [
    'student1',
    'grader-course101',
    'grader-course123',
    'grader-demo',
    'tele',
    'grader-demo11',
    'grader-demo123',
]

# instructor1 and instructor2 have access to different shared servers.
# Note that groups providing access to the formgrader *must* start with
# 'formgrade-', and groups providing access to course materials *must*
# start with 'nbgrader-' in order for nbgrader to work correctly.
c.JupyterHub.load_groups = {
    'instructors': [
    ],
    'formgrade-course101': [
        'grader-course101',
    ],
    'formgrade-course123': [
        'grader-course123',
    ],
    'formgrade-demo': [
        'grader-demo',
    ],
    'nbgrader-course101': [
        'student1',
    ],
    'nbgrader-course123': [
        'student1',
    ],
    'nbgrader-demo': [
        'student1',
    ],
    'formgrade-demo11': [
        'grader-demo11',
    ],
    'nbgrader-demo11': [
        'student1',
    ],
    'formgrade-demo123': [
        'grader-demo123',
    ],
    'nbgrader-demo123': [
        'student1',
    ],
}

c.JupyterHub.load_roles = roles = [
    {
        'name': 'instructor',
        'groups': ['instructors'],
        'scopes': [
            # these are the scopes required for the admin UI
            'admin:users',
            'admin:servers',
        ],
    },
    # The class_list extension needs permission to access services
    {
        'name': 'server',
        'scopes': [
            'inherit',
            # in JupyterHub 2.4, this can be a list of permissions
            # greater than the owner and the result will be the intersection;
            # until then, 'inherit' is the only way to have variable permissions
            # for the server token by user
            # "access:services",
            # "list:services",
            # "read:services",
            # "users:activity!user",
            # "access:servers!user",
        ],
    },
]
for course in ['course101', 'course123','demo','demo11','demo123']:
    # access to formgrader
    roles.append(
        {
            'name': f'formgrade-{course}',
            'groups': [f'formgrade-{course}'],
            'scopes': [
                f'access:services!service={course}',
            ],
        }
    )
    # access to course materials
    roles.append(
        {
            'name': f'nbgrader-{course}',
            'groups': [f'nbgrader-{course}'],
            'scopes': [
                # access to the services API to discover the service(s)
                'list:services',
                f'read:services!service={course}',
            ],
        }
    )


# Start the notebook server as a service. The port can be whatever you want
# and the group has to match the name of the group defined above.
c.JupyterHub.services = [

    {
        'name': 'demo123',
        'url': 'http://127.0.0.1:10001',
        'command': [
            'jupyterhub-singleuser',
            '--debug',
        ],
        'user': 'grader-demo123',
        'cwd': '/home/grader-demo123',
        'environment': {
            'JUPYTERHUB_DEFAULT_URL': '/lab'
        },
        'api_token': 'FmiQ2cRhWpeubEZw',
    },

    {
        'name': 'demo11',
        'url': 'http://127.0.0.1:10000',
        'command': [
            'jupyterhub-singleuser',
            '--debug',
        ],
        'user': 'grader-demo11',
        'cwd': '/home/grader-demo11',
        'environment': {
            'JUPYTERHUB_DEFAULT_URL': '/lab'
        },
        'api_token': 'ICD7sRzORL9wuXgq',
    },

    {
        'name': 'course101',
        'url': 'http://127.0.0.1:9999',
        'command': [
            'jupyterhub-singleuser',
            '--debug',
        ],
        'user': 'grader-course101',
        'cwd': '/home/grader-course101',
        'environment': {
            # specify lab as default landing page
            'JUPYTERHUB_DEFAULT_URL': '/lab'
        },
        'api_token': 'fd6e0db39e534f6e91e415c01643cf3f',
    },
    {
        'name': 'course123',
        'url': 'http://127.0.0.1:9998',
        'command': [
            'jupyterhub-singleuser',
            '--debug',
        ],
        'user': 'grader-course123',
        'cwd': '/home/grader-course123',
        'environment': {
            # specify lab as default landing page
            'JUPYTERHUB_DEFAULT_URL': '/lab'
        },
        'api_token': '6034d46a00834163aa6f20cf1f23e5e3',
    },
    {
        'name': 'demo',
        'url': 'http://127.0.0.1:9997',
        'command': [
            'jupyterhub-singleuser',
            '--debug',
        ],
        'user': 'grader-demo',
        'cwd': '/home/grader-demo',
        'environment': {
            # specify lab as default landing page
            'JUPYTERHUB_DEFAULT_URL': '/lab'
        },
        'api_token': 'bbe9e4f6d3564f61b1613a2c90f8b2f8',
    },
]
