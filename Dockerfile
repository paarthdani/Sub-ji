FROM python:3.9.7-slim-buster
WORKDIR /subji
ADD . /subji
RUN pip install -r requirements.txt
CMD ["python", "subji.py"]