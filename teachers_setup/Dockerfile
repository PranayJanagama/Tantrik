FROM base_nbgrader:latest

WORKDIR /srv/nbgrader/jupyterhub

RUN apt-get update && apt-get -y upgrade && \
    apt-get install -y build-essential libmysqlclient-dev && \
    apt-get install -y pkg-config iputils-ping openssh-client

# Generate SSH key pair if not already existing
RUN mkdir -p /root/.ssh && \
    ssh-keygen -t rsa -b 4096 -f /root/.ssh/id_rsa -N "" && \
    chmod 600 /root/.ssh/id_rsa


COPY setup_pages/api.py /srv/nbgrader/nbgrader/nbgrader/apps/api.py
COPY setup_pages/generate_feedback.py /srv/nbgrader/nbgrader/nbgrader/converters/generate_feedback.py
COPY setup_pages/handlers.py /srv/nbgrader/nbgrader/nbgrader/server_extensions/assignment_list/handlers.py
COPY setup_pages/manage_assignments.tpl /srv/nbgrader/nbgrader/nbgrader/server_extensions/formgrader/templates/manage_assignments.tpl
COPY setup_pages/native-login.html /usr/local/lib/python3.10/dist-packages/nativeauthenticator/templates/native-login.html
COPY setup_pages/page.html /usr/local/lib/python3.10/dist-packages/nativeauthenticator/templates/page.html
COPY setup_pages/signup.html /usr/local/lib/python3.10/dist-packages/nativeauthenticator/templates/signup.html
COPY setup_pages/users.py /usr/local/lib/python3.10/dist-packages/jupyterhub/apihandlers/users.py
COPY setup_pages/groups.py /usr/local/lib/python3.10/dist-packages/jupyterhub/apihandlers/groups.py
COPY setup_pages/validategradescore.py /srv/nbgrader/nbgrader/nbgrader/preprocessors/validategradescore.py

WORKDIR /srv/nbgrader/nbgrader

# Only in Teacher setup

RUN ["jupyter", "labextension", "enable", "--level=sys_prefix", "@jupyter/nbgrader:create-assignment"]
RUN ["jupyter", "labextension", "enable", "--level=sys_prefix", "@jupyter/nbgrader:formgrader"]
RUN ["jupyter", "server", "extension", "enable", "--user", "nbgrader.server_extensions.formgrader"]

COPY setup_pages/setup_script.sh /usr/local/bin/setup_script.sh
RUN chmod +x /usr/local/bin/setup_script.sh

WORKDIR /srv/nbgrader/jupyterhub

EXPOSE 8000
EXPOSE 8581

# CMD ["/bin/bash", "-c", "/usr/local/bin/setup_script.sh  && exec /usr/local/bin/jupyterhub", "&&", "cd", "/home/tele/Music/Tantrik_Testcenter", "&&", "source", ".venv/bin/activate", "&&", "flask", "run", "--host=0.0.0.0", "--port=8581", "--debug"]

CMD /bin/bash -c "/usr/local/bin/setup_script.sh && \
    exec /usr/local/bin/jupyterhub & \
    cd /home/tele/Music/Tantrik_Testcenter && \
    source .venv/bin/activate && \
    flask run --host=0.0.0.0 --port=8581 --debug"