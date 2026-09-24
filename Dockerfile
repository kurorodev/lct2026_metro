FROM ros:humble-ros-base-jammy@sha256:1813d3c85d7f96ff7d3012d865204583255740182db5d0065f8f8cd029a83138
ENV PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1 OPENBLAS_NUM_THREADS=1
ENV FASTRTPS_DEFAULT_PROFILES_FILE=/app/config/fastdds.xml
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip ros-humble-sensor-msgs-py ros-humble-visualization-msgs \
    ros-humble-rosbag2-storage-default-plugins ros-humble-rviz2 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements-runtime.txt ./
RUN python3 -m pip install --no-cache-dir -r requirements-runtime.txt
COPY pyproject.toml setup.py ./
COPY metro_guard ./metro_guard
RUN python3 -m pip install --no-cache-dir --no-deps . \
    && cd /tmp && python3 -c "from metro_guard import __version__; print(__version__)" \
    && python3 -c "from pathlib import Path; import metro_guard; assert (Path(metro_guard.__file__).parent / 'web' / 'review.js').is_file()" \
    && metro-guard --help
COPY config ./config
COPY scripts ./scripts
COPY tests ./tests
COPY rviz ./rviz
RUN python3 -m unittest discover -s tests -v
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["help"]
