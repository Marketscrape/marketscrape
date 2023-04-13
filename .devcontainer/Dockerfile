FROM python:3.10

ENV PYTHONUNBUFFERED=1

WORKDIR /code

COPY requirements.txt .

RUN pip install -r requirements.txt
RUN python3 -c "import nltk; nltk.download('all')"

COPY . .

EXPOSE 8000

ENTRYPOINT [ "python", "manage.py"]
CMD ["runserver", "0.0.0.0:8000"]