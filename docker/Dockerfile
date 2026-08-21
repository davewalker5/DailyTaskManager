FROM python:3.13-slim-bullseye

ARG VERSION

COPY dailytaskmanager-${VERSION}.0 /opt/dailytaskmanager

WORKDIR /opt/dailytaskmanager

RUN apt-get update -y
RUN pip install --no-cache-dir /opt/dailytaskmanager/daily_task_manager-${VERSION}-py3-none-any.whl
RUN test -f /opt/dailytaskmanager/migrations/0001_initial.py
RUN test -f /opt/dailytaskmanager/streamlit_app.py

ENV DAILY_TASK_MANAGER_ROOT=/opt/dailytaskmanager
ENV DAILY_TASK_MANAGER_DB=/var/opt/dailytaskmanager/taskmanager.db

ENTRYPOINT [ "streamlit" ]
CMD ["run", "/opt/dailytaskmanager/streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501"]
