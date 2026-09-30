FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir \
      fastapi \
      uvicorn \
      psycopg2-binary \
      python-dotenv \
      "passlib[bcrypt]" \
      "bcrypt<4.1" \
      "python-jose[cryptography]" \
      pydantic

COPY scripts /app/scripts

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "scripts.api_v2:app", "--host", "0.0.0.0", "--port", "8000"]
