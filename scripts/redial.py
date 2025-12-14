import KSR as KSR

ACME_DOMAIN = "acme.operador"

# Mandatory function - module initiation
def mod_init():
    KSR.info("===== Redial 2.0 Sprint 1: Python mod init\n")
    return kamailio()

class kamailio:
    # Mandatory function - Kamailio class initiation
    def __init__(self):
        KSR.info('===== Redial 2.0 Sprint 1: kamailio.__init__\n')

    # Mandatory function - Kamailio subprocesses
    def child_init(self, rank):
        KSR.info('===== Redial 2.0 Sprint 1: kamailio.child_init(%d)\n' % rank)
        return 0

    # Function called for REQUEST messages received
    def ksr_request_route(self, msg):

        # REGISTER / DEREGISTER
        if msg.Method == "REGISTER":
            from_domain = KSR.pv.get("$fd")  # domínio do From-URI
            KSR.info("REGISTER From domain: " + str(from_domain) + "\n")
            KSR.info("REGISTER To: " + (KSR.pv.get("$tu") or "") +
                     " Contact: " + (KSR.hdr.get("Contact") or "") + "\n")

            # Rejeitar utilizadores fora do domínio ACME
            if from_domain != ACME_DOMAIN:
                KSR.info("REGISTER rejected (invalid domain)\n")
                KSR.sl.send_reply(403, "Forbidden - Invalid Domain")
                return 1

            # Guardar (REGISTER ou deregister) no usrloc/location
            if KSR.registrar.save("location", 0) < 0:
                KSR.err("Error saving registration\n")
                KSR.sl.send_reply(500, "Server Error")
                return 1

            # O registrar/usrloc gera a resposta 200 OK
            return 1

        # Tudo o resto ainda não implementado no Sprint 1
        KSR.sl.send_reply(403, "Forbidden method for Sprint 1")
        return 1

    # Function called for REPLY messages received
    def ksr_reply_route(self, msg):
        KSR.info("===== Redial 2.0 Sprint 1: reply_route - Status: " +
                 str(KSR.pv.get("$rs")) + "\n")
        return 1

    # Function called for messages sent/transit
    def ksr_onsend_route(self, msg):
        KSR.info("===== Redial 2.0 Sprint 1: onsend_route: %s\n" % (msg.Type))
        return 1
