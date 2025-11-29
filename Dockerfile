FROM debian:11

RUN apt update && apt install -y kamailio kamailio-python3-modules python3 python3-pip

COPY Kamailio/redial.py /usr/share/kamailio/python/
COPY Kamailio/kamailio.cfg /etc/kamailio/kamailio.cfg

CMD ["kamailio", "-f", "/etc/kamailio/kamailio.cfg", "-dd"]
