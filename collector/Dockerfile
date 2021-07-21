FROM python:latest
RUN pip install virtualenv
RUN virtualenv venv
COPY . /src
RUN pip install -r /src/requirements.txt
CMD python /src/main.py
