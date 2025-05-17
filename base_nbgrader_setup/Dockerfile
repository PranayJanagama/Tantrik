# Base setup image
FROM ubuntu:20.04 as setup

ENV DEBIAN_FRONTEND=noninteractive

# User creation
RUN useradd -ms /bin/bash tele && echo "tele:tele123" | chpasswd && adduser tele sudo

# Install Python 3.10 and basic tools
RUN apt-get update && apt-get -y upgrade && \
    apt-get install -y git sudo curl software-properties-common build-essential libssl-dev && \
    add-apt-repository ppa:deadsnakes/ppa -y && \
    apt-get update && \
    apt-get -y install python3.10 python3.10-venv python3.10-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install pip for Python 3.10 properly
RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py && \
    python3.10 get-pip.py && rm get-pip.py

# Symlink pip3 to python3.10 pip (so `pip3` is available globally)
RUN ln -s /usr/local/bin/pip3.10 /usr/bin/pip3 && \
    ln -s /usr/local/bin/pip3.10 /usr/bin/pip

# Python package installations
RUN python3.10 -m pip install --upgrade wheel html5lib PyYAML && \
    python3.10 -m pip install torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu118 && \
    python3.10 -m pip install -U scikit-learn scipy matplotlib tqdm torch-summary sentence-transformers transformers gensim && \
    python3.10 -m pip install jupyterhub-nativeauthenticator numpy pandas matplotlib

# Install Node.js
RUN curl -fsSL https://nodejs.org/dist/v16.17.1/node-v16.17.1-linux-x64.tar.xz -o node.tar.xz && \
    tar -xf node.tar.xz -C /usr/local --strip-components=1 && \
    rm node.tar.xz && \
    ln -s /usr/local/bin/node /usr/bin/node && \
    ln -s /usr/local/bin/npm /usr/bin/npm

# Copy JupyterHub + nbgrader setup scripts
COPY ./srv /srv

# Ensure script is executable
RUN chmod +x /srv/nbgrader/nbgrader/demos/*.sh

WORKDIR /srv/nbgrader/nbgrader/demos

# Run JupyterHub and nbgrader setup **only once**
RUN /srv/nbgrader/nbgrader/demos/restart_demo.sh demo_multiple_classes

# Expose JupyterHub port
EXPOSE 8000

# Set working directory for derived images
WORKDIR /srv/nbgrader/jupyterhub