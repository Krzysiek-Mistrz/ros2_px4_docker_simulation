from setuptools import setup

package_name = 'dron_nav_pkg'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='TwojeImię',
    maintainer_email='twoj.email@example.com',
    description='PX4 mission control node',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'dron_nav_pkg = dron_nav_pkg.dron_nav_pkg:main',
        ],
    },
)
