FROM python:3.6.8-stretch

# Upgrade pip
RUN pip install --upgrade pip

## make a local directory
RUN mkdir /app

# set "app" as the working directory from which CMD, RUN, ADD references
COPY . /app
WORKDIR /app
# RUN /bin/bash -c "ls"

# pip install the local requirements.txt
RUN pip install -r requirements.txt
EXPOSE 7800

# Define our command to be run when launching the container
ENTRYPOINT ["sh", "./start.sh"]
