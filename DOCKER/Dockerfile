FROM owasp/zap2docker-stable:latest
MAINTAINER Ben Lu
USER root
ENV ZAP_KEY hahaha

RUN apt-get update;\
apt-get install -y git sudo 
RUN sudo git clone https://github.com/luben3485/Web_App_Scanner.git /Web_App_Scanner
RUN sudo apt-get update;\
     sudo apt-get -y upgrade;\
     sudo apt-get install -y python3 python3-pip

RUN sudo pip3 install flask requests pymongo requests-html flask-cors rsa
EXPOSE 8080
WORKDIR /Web_App_Scanner/Web
