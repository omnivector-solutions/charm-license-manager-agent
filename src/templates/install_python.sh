#!/bin/bash

PYTHON38_VERSION="3.8.10"

# install python3.8.10

 mkdir ./tmp/
 wget https://www.python.org/ftp/python/${PYTHON38_VERSION}/Python-${PYTHON38_VERSION}.tgz -P ./tmp/
 tar xvf ./tmp/Python-${PYTHON38_VERSION}.tgz -C ./tmp/
 cd ./tmp/Python-${PYTHON38_VERSION}/
 ./configure --enable-optimizations
 make altinstall
 cd ../../
 rm -rf tmp/
