# VMware vSphere Python SDK Community Samples
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from setuptools import setup
import os


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(name='pyvmomi-community-samples',
      version='5.5.0_2014.dev',
      description='VMware vSphere Python SDK Community Samples',
      author='VMware, Inc.',
      author_email='hartsocks@vmware.com',
      url='http://vmware.github.io/pyvmomi-community-samples/',
      install_requires=['pyvmomi'],
      packages=['samples'],
      test_suite='samples.tests',
      license='Apache',
      long_description=read('README.md'),
      classifiers=[
          "License :: OSI Approved :: Apache Software License",
          "Development Status :: 4 - Beta",
          "Environment :: No Input/Output (Daemon)",
          "Intended Audience :: Information Technology",
          "Intended Audience :: System Administrators",
          "Topic :: Software Development :: Libraries :: Python Modules",
          "Topic :: System :: Distributed Computing"
      ],
      zip_safe=True)
