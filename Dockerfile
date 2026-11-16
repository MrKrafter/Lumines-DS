FROM python:3.12-alpine
WORKDIR /app
COPY lumines_server.py .
ENV LUMINES_DATA=/data/scores.json
VOLUME /data
EXPOSE 27620/udp 27621/tcp
USER nobody
CMD ["python3", "lumines_server.py"]
