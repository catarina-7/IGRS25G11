import KSR as KSR

ACME_DOMAIN = "acme.operador"
REDIAL_LISTA = {}

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
            from_uri = KSR.pv.get("$fu") or "" # AoR do From
            to_uri = KSR.pv.get("$tu") or "" # AoR do To

            contact_hdr = KSR.hdr.get("Contact") or ""
            expires_hdr = (KSR.hdr.get("Expires") or "").strip()
            
            KSR.info(f"REGISTER From: {from_uri} (domain: {from_domain})\n")
            KSR.info("REGISTER To: " + (to_uri) +
                     " Contact: " + contact_hdr + "\n") # Extrair AoR do pedido REGISTER (From/To)

            # Rejeitar utilizadores fora do domínio ACME / Validar domínio do AoR
            if from_domain != ACME_DOMAIN:
                KSR.info("REGISTER rejected (invalid domain)\n") # Log de tentativa rejeitada
                KSR.sl.send_reply(403, "Forbidden - Invalid Domain") # Rejeitar pedido com resposta SIP adequada (403 Forbidden)
                return 1 # Garante que nenhum estado ou lista é criado
            
            expires = None
            if expires_hdr.isdigit():
                expires = int(expires_hdr)

            is_deregister = (expires == 0) or ("expires=0" in contact_hdr.replace(" ", ""))
            if is_deregister:
                KSR.info("DEREGISTER detetado para " + (to_uri) + "\n")
                
                # Detetar se utilizador está registado antes de remover
                KSR.pv.sets("$ru", to_uri)
                is_registered = (KSR.registrar.lookup("location") == 1)

                if not is_registered:
                    KSR.info("DEREGISTER: utilizador não estava registado: " + (to_uri) + "\n")
                    # 404 se não existir registo
                    KSR.sl.send_reply(404, "Not Found (not registered)")
                    return 1

            # Atualizar estado de registo na BD (Guarda (REGISTER ou deregister) no usrloc/location)
            # Responder SIP 200 OK com Contact e expires
            if KSR.registrar.save("location", 0) < 0:
                KSR.err("Error saving registration\n")
                KSR.sl.send_reply(500, "Server Error")
                return 1

            # O registrar gera a resposta 200 OK e inclui Contact e Expires
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
