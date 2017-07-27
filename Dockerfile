FROM alpine

RUN apk add --no-cache --update openssh git python3 python3-dev build-base bash cron
RUN pip3 install pipenv

RUN mkdir -p /app
WORKDIR /app
COPY Pipfile  /app/Pipfile
COPY Pipfile.lock  /app/Pipfile.lock
RUN pipenv install

ENV APP_DIR /app
ENV FLASK_APP app.py

# The root of the project needs to be mounted at /app at run time
#    docker run -v $(PWD):/app
WORKDIR ${APP_DIR}
VOLUME ${APP_DIR}
EXPOSE 5000

# Cleanup
RUN rm -rf /.wh /root/.cache /var/cache

CMD pipenv run python app.py
