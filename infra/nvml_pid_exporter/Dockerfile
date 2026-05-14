FROM python:3.12-slim
RUN pip install --no-cache-dir nvidia-ml-py prometheus-client
COPY exporter.py /exporter.py
ENV NVML_PID_PORT=9401
EXPOSE 9401
CMD ["python", "-u", "/exporter.py"]
