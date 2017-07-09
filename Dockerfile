FROM alpine

RUN apk add --no-cache --update openssh git python3 python3-dev build-base bash 
RUN pip3 install pipenv

RUN mkdir -p /tmp
WORKDIR /tmp
COPY Pipfile  /tmp/Pipfile
COPY Pipfile.lock  /tmp/Pipfile.lock
RUN pipenv install

ENV APP_DIR /app
ENV FLASK_APP app.py

# The CWD needs to be mounted at /app at run time
WORKDIR ${APP_DIR}
VOLUME ${APP_DIR}
EXPOSE 5000

# Cleanup
RUN rm -rf /.wh /root/.cache /var/cache /tmp/requirements.txt

CMD python3 app.py
