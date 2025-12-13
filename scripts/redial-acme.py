import sys
import KSR as KSR

ACME_DOMAIN = "acme.operador"
PIN_CODE = "00000"

#Estruturas em memoria
REDIAL_LISTS = {}
SERVICE_ACTIVE = {}

# Mandatory function - module initiation
def mod_init():
    KSR.info("===== Redial 2.0: Python mod init\n")
    return kamailio()

class kamailio:
    # Mandatory function - Kamailio class initiation
    def __init__(self):
        KSR.info('===== Redial 2.0: kamailio.__init__\n')

    # Mandatory function - Kamailio subprocesses
    def child_init(self, rank):
        KSR.info('===== Redial 2.0: kamailio.child_init(%d)\n' % rank)
        return 0

    # Function called for REQUEST messages received 
    def ksr_request_route(self, msg):
        ruri = KSR.pv.get("$ru")
        from_uri = KSR.pv.get("$fu")
        to_uri = KSR.pv.get("$tu")
        to_domain = KSR.pv.get("$td")

        KSR.info("INVITE R-URI: " + ruri + "\n")
        KSR.info("From: " + from_uri +" To: " + to_uri +"\n")
        
        # Registo (US1, US2, US3)
        if  (msg.Method == "REGISTER"):
            return self.handle_register(to_uri, to_domain)
        
        # Mensagens do servico (US3, US5, US6, US7)
        if (msg.Method == "MESSAGE"):
            return self.handle_message(ruri, from_uri)
        
        # Restantes metodos (ex: INVITE) sao tratados no proximo sprint
        KSR.sl.send_reply(403, "Forbidden method for Sprint 1")
        
        return 1        

    # Function called for REPLY messages received
    def ksr_reply_route(self, msg):
        KSR.info("===== Redial 2.0: reply route - from kamailio python script\n")
        KSR.info("      Status is: " + str(KSR.pv.get("$rs")) + "\n")
        return 1

    # Function called for messages sent/transit
    def ksr_onsend_route(self, msg):
        KSR.info("===== Redial 2.0: onsend route - from kamailio python script\n")
        KSR.info("      %s\n" %(msg.Type))
        return 1

    def handle_register(self, to_uri, to_domain):
        # US2 - Rejeitar registos vindos de outros dominios
        if to_domain != ACME_DOMAIN:
            KSR.info("REGISTER rejeitado para domínio\n")
            KSR.sl.send_reply(403, "Forbiddeen - Invalid Domain ")
            return 1
        
        # US4 - Verificar se é de-registo
        expires_hdr = KSR.hdr.get("Expires")
        expires = -1
        if expires_hdr is not None and expires_hdr != "":
            try:
                expires = int(expires_hdr.strip())
            except ValueError:
                expires = -1
        
        if expires == 0:
            KSR.info("DEREGISTER para {to_uri}\n")
            if KSR.registrar.save("location", 0) < 0:
                KSR.err("Erro no DEREGISTER\n")
                KSR.sl.send_reply(500, "Server Error")
                return 1
            
            # Limpar na memoria
            if to_uri in REDIAL_LISTS:
                del REDIAL_LISTS[to_uri]
            if to_uri in SERVICE_ACTIVE:
                del SERVICE_ACTIVE[to_uri]
            return 1
        
        # US1 - Registar utilizador ACME
        KSR.info("REGISTER R-URI: " + KSR.pv.get("$ru") + "\n")
        KSR.info("            To: " + KSR.pv.get("$tu") +
                 " Contact: " + KSR.hdr.get("Contact") + "\n")

        if KSR.registrar.save('location', 0) < 0:
            KSR.err("Erro ao guardar registo\n")
            KSR.sl.send_reply(500, "Server Error")
            return 1

        # Inicializar estado do Redial
        REDIAL_LISTS.setdefault(to_uri, [])
        SERVICE_ACTIVE.setdefault(to_uri, False)

        KSR.info(f"REGISTER OK para {to_uri}\n")
        return 1

    # ==========================
    #  MESSAGE (US3, US5, US6, US7)
    # ==========================
    def handle_message(self, ruri, from_uri):
        body = (KSR.pv.get("$rb") or "").strip()

        KSR.info(f"MESSAGE para {ruri} de {from_uri} com corpo: '{body}'\n")

        # US3 - Validacao de PIN
        if ruri.startswith(f"sip:validar@{ACME_DOMAIN}"):
            return self.handle_pin(from_uri, body)

        # US5/US6/US7 - Gestão do serviço Redial
        if ruri.startswith(f"sip:redial@{ACME_DOMAIN}"):
            return self.handle_redial_command(from_uri, body)

        # Outros MESSAGE não são tratados neste sprint
        KSR.sl.send_reply(404, "Not here")
        return 1

    # US3 - Validar PIN
    def handle_pin(self, from_uri, body):
        if body == PIN_CODE:
            KSR.info(f"PIN correto para {from_uri}\n")
            KSR.sl.send_reply(200, "PIN OK")
        else:
            KSR.info(f"PIN incorreto para {from_uri}\n")
            KSR.sl.send_reply(403, "Invalid PIN")
        return 1

    # US5/US6/US7 - ACTIVATE / DEACTIVATE / modificar lista
    def handle_redial_command(self, from_uri, body):
        if not body:
            KSR.sl.send_reply(400, "Empty body")
            return 1

        parts = body.split()
        command = parts[0].upper()
        dests = parts[1:]

        # Garantir que o utilizador existe nas estruturas
        REDIAL_LISTS.setdefault(from_uri, [])
        SERVICE_ACTIVE.setdefault(from_uri, False)

        if command == "ACTIVATE":
            # US5 + US7 – ativar serviço e substituir lista
            REDIAL_LISTS[from_uri] = dests[:]
            SERVICE_ACTIVE[from_uri] = True

            KSR.info(f"ACTIVATE de {from_uri} -> {REDIAL_LISTS[from_uri]}\n")
            KSR.sl.send_reply(200, "Service Activated")
            return 1

        if command == "DEACTIVATE":
            # US6 – desativar serviço e limpar lista
            REDIAL_LISTS[from_uri] = []
            SERVICE_ACTIVE[from_uri] = False

            KSR.info(f"DEACTIVATE de {from_uri}\n")
            KSR.sl.send_reply(200, "Service Deactivated")
            return 1

        KSR.info(f"Comando inválido em MESSAGE: {body}\n")
        KSR.sl.send_reply(400, "Invalid Command")
        return 1
        
