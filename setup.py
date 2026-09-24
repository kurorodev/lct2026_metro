from setuptools import find_packages, setup

setup(
    name='metro-lidar-guard', version='0.2.0',
    description='Reproducible ROS 2 tunnel obstacle detection baseline',
    packages=find_packages(include=['metro_guard', 'metro_guard.*']),
    package_data={'metro_guard':['web/*.html','web/*.js']},
    python_requires='>=3.8',
    install_requires=['numpy>=1.24,<2','rosbags==0.9.23'],
    entry_points={'console_scripts':['metro-guard=metro_guard.cli:main']},
)
